package ru.rshb.playground.efr;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Данные заглушки ЕФР в памяти: пользователи, клиенты, карты, история операций.
 * Состояние живёт, пока запущен процесс, и сбрасывается при перезапуске.
 */
public class EfrStore {

    public static final long CASH_LIMIT_MAX = 500_000;
    public static final long ONLINE_LIMIT_MAX = 300_000;

    /** Через сколько после заявки на перевыпуск новая карта переходит в статус «Заказана». */
    static final long REISSUE_PROCESSING_MS = 20_000;

    private static final DateTimeFormatter HISTORY_TIME = DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm:ss");
    private static final DateTimeFormatter EXPIRY = DateTimeFormatter.ofPattern("MM/yy");

    private static final String[][] PEOPLE = {
            {"Кузнецов Андрей Викторович", "ANDREY KUZNETSOV"},
            {"Соколова Мария Дмитриевна", "MARIA SOKOLOVA"},
            {"Попов Сергей Николаевич", "SERGEY POPOV"},
            {"Лебедева Анна Игоревна", "ANNA LEBEDEVA"},
            {"Новиков Дмитрий Алексеевич", "DMITRY NOVIKOV"},
            {"Морозова Елена Сергеевна", "ELENA MOROZOVA"},
            {"Волков Павел Андреевич", "PAVEL VOLKOV"},
            {"Фёдорова Ольга Владимировна", "OLGA FEDOROVA"},
    };

    public enum Role { MANAGER, OPERATOR, SUPERVISOR }

    public record User(String login, String password, String fullName, Role role) {
    }

    public static final class Client {
        public String clientId;
        public String fullName;
        public String holderName;
        public String phone;
        public String passportSeries;
        public String passportNumber;
        public final List<Card> cards = new ArrayList<>();
    }

    public static final class Card {
        public String cardNumber;
        public String clientId;
        public String holderName;
        public String expiry;
        public String accountNumber;
        public String status;
        public String blockReason;
        public String balance = "0,00 ₽";
        public long cashLimit = 100_000;
        public long onlineLimit = 50_000;
        public long transferLimit = 200_000;
        /** Для перевыпущенной карты — момент, когда заказ завершится. */
        public long readyAt;
        public final List<Map<String, String>> history = new ArrayList<>();

        public String digits() {
            return cardNumber.replace(" ", "");
        }

        public String lastDigits() {
            return cardNumber.substring(cardNumber.length() - 4);
        }

        public String currentStatus() {
            if ("В обработке".equals(status) && System.currentTimeMillis() >= readyAt) {
                status = "Заказана";
            }
            return status;
        }
    }

    private final Map<String, User> users = new LinkedHashMap<>();
    private final Map<String, Client> clients = new LinkedHashMap<>();
    private final Map<String, Card> cards = new LinkedHashMap<>();
    private final AtomicLong clientSeq = new AtomicLong(100_000);

    public EfrStore() {
        addUser(new User("rf_card_mng1", "Mng1#Playground", "Смирнова Ольга Петровна", Role.MANAGER));
        addUser(new User("rf_m_oper4", "Oper4#Playground", "Григорьев Олег Ильич", Role.OPERATOR));
        addUser(new User("rf_card_sup1", "Kart0chka#2026", "Белова Ирина Сергеевна", Role.SUPERVISOR));
        addUser(new User("ivanov_ii", "Iv@nov_2026", "Иванов Иван Иванович", Role.MANAGER));

        // Постоянный клиент стенда: на нём часто «тренируются» вручную
        Client regular = newClient(PEOPLE[0], "4510", "123456");
        Card card = newCard(regular, "2200 7001 2345 6789");
        card.balance = "48 210,37 ₽";
    }

    private void addUser(User user) {
        users.put(user.login(), user);
    }

    public synchronized Optional<User> authenticate(String login, String password) {
        User user = users.get(login);
        return user != null && user.password().equals(password) ? Optional.of(user) : Optional.empty();
    }

    public synchronized Optional<User> user(String login) {
        return Optional.ofNullable(users.get(login));
    }

    public synchronized Client createClient() {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        String series;
        String number;
        do {
            series = "%02d%02d".formatted(random.nextInt(1, 99), random.nextInt(0, 26));
            number = "%06d".formatted(random.nextInt(1_000_000));
        } while (findClient(series, number).isPresent());
        return newClient(PEOPLE[random.nextInt(1, PEOPLE.length)], series, number);
    }

    private Client newClient(String[] person, String series, String number) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        Client client = new Client();
        client.clientId = String.valueOf(clientSeq.incrementAndGet());
        client.fullName = person[0];
        client.holderName = person[1];
        client.phone = "+7 9%02d %03d-%02d-%02d".formatted(random.nextInt(100), random.nextInt(1000),
                random.nextInt(100), random.nextInt(100));
        client.passportSeries = series;
        client.passportNumber = number;
        clients.put(client.clientId, client);
        return client;
    }

    public synchronized Optional<Client> findClient(String series, String number) {
        return clients.values().stream()
                .filter(c -> c.passportSeries.equals(series) && c.passportNumber.equals(number))
                .findFirst();
    }

    public synchronized Optional<Client> client(String clientId) {
        return Optional.ofNullable(clients.get(clientId));
    }

    public synchronized Optional<Card> card(String digits) {
        return Optional.ofNullable(cards.get(digits));
    }

    public synchronized Card issueDebitCard(Client client, String login) {
        Card card = newCard(client, randomCardNumber(client));
        addHistory(card, "Выпуск карты", login);
        return card;
    }

    private Card newCard(Client client, String cardNumber) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        Card card = new Card();
        card.cardNumber = cardNumber;
        card.clientId = client.clientId;
        // Держатель — ФИО клиента, как в шапке продуктового профиля
        card.holderName = client.fullName;
        card.expiry = LocalDate.now().plusYears(4).format(EXPIRY);
        card.accountNumber = "40817810%012d".formatted(random.nextLong(1_000_000_000_000L));
        card.status = "Активна";
        client.cards.add(card);
        cards.put(card.digits(), card);
        return card;
    }

    private String randomCardNumber(Client client) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        String number;
        do {
            number = "2200 70%02d %04d %04d".formatted(random.nextInt(100), random.nextInt(10_000),
                    random.nextInt(10_000));
            String last = number.substring(number.length() - 4);
            if (client.cards.stream().anyMatch(c -> c.lastDigits().equals(last))) {
                number = null;
            }
        } while (number == null || cards.containsKey(number.replace(" ", "")));
        return number;
    }

    public synchronized void block(Card card, String reason, String login) {
        requireStatus(card, "Активна", "Заблокировать можно только активную карту");
        if (reason == null || reason.isBlank()) {
            throw new EfrException(400, "Укажите причину блокировки");
        }
        card.status = "Заблокирована";
        card.blockReason = reason;
        addHistory(card, "Блокировка карты. Причина: " + reason, login);
    }

    public synchronized void blockTemporarily(Card card, String login) {
        requireStatus(card, "Активна", "Временно заблокировать можно только активную карту");
        card.status = "Временно заблокирована";
        addHistory(card, "Временная блокировка карты", login);
    }

    public synchronized void removeTemporaryBlock(Card card, String login) {
        requireStatus(card, "Временно заблокирована", "Карта не заблокирована временно");
        card.status = "Активна";
        addHistory(card, "Снятие временной блокировки", login);
    }

    public synchronized void close(Card card, String login) {
        requireStatus(card, "Активна", "Закрыть можно только активную карту");
        if (!"0,00 ₽".equals(card.balance)) {
            throw new EfrException(409, "Карту с ненулевым остатком закрыть нельзя");
        }
        card.status = "Закрыта";
        addHistory(card, "Закрытие карты", login);
    }

    public synchronized void unblock(Card card, String supervisorLogin, String supervisorPassword, String login) {
        requireStatus(card, "Заблокирована", "Разблокировать можно только заблокированную карту");
        if (isBlank(supervisorLogin) || isBlank(supervisorPassword)) {
            throw new EfrException(403, "Требуется подтверждение старшего менеджера");
        }
        User supervisor = authenticate(supervisorLogin, supervisorPassword)
                .orElseThrow(() -> new EfrException(403, "Неверный логин или пароль старшего менеджера"));
        if (supervisor.role() != Role.SUPERVISOR) {
            throw new EfrException(403, "Пользователь %s не является старшим менеджером".formatted(supervisorLogin));
        }
        card.status = "Активна";
        card.blockReason = null;
        addHistory(card, "Разблокировка карты. Подтвердил: " + supervisorLogin, login);
    }

    public synchronized void setLimits(Card card, String cash, String online, String transfer, String login) {
        requireStatus(card, "Активна", "Лимиты можно менять только у активной карты");
        long newCash = parseLimit(cash, card.cashLimit, CASH_LIMIT_MAX);
        long newOnline = parseLimit(online, card.onlineLimit, ONLINE_LIMIT_MAX);
        long newTransfer = parseLimit(transfer, card.transferLimit, 1_000_000);
        if (newCash != card.cashLimit) {
            addHistory(card, "Изменение лимита «Снятие наличных»: " + money(newCash), login);
        }
        if (newOnline != card.onlineLimit) {
            addHistory(card, "Изменение лимита «Покупки в интернете»: " + money(newOnline), login);
        }
        if (newTransfer != card.transferLimit) {
            addHistory(card, "Изменение лимита «Переводы»: " + money(newTransfer), login);
        }
        card.cashLimit = newCash;
        card.onlineLimit = newOnline;
        card.transferLimit = newTransfer;
    }

    public synchronized Card reissue(Card card, String reason, String login) {
        requireStatus(card, "Активна", "Перевыпустить можно только активную карту");
        if (isBlank(reason)) {
            throw new EfrException(400, "Укажите причину перевыпуска");
        }
        Client client = clients.get(card.clientId);
        card.status = "Закрыта";
        addHistory(card, "Перевыпуск карты. Причина: " + reason, login);

        Card newCard = newCard(client, randomCardNumber(client));
        newCard.status = "В обработке";
        newCard.readyAt = System.currentTimeMillis() + REISSUE_PROCESSING_MS;
        addHistory(newCard, "Заказ карты взамен •••• " + card.lastDigits(), login);
        return newCard;
    }

    private static long parseLimit(String value, long current, long max) {
        if (value == null) {
            return current;
        }
        String digits = value.replace(" ", "").replace(" ", "");
        if (!digits.matches("\\d{1,9}")) {
            throw new EfrException(400, "Лимит не изменён. Введите сумму целым числом");
        }
        long limit = Long.parseLong(digits);
        if (limit > max) {
            throw new EfrException(400, "Лимит не изменён. Превышен максимальный лимит " + money(max));
        }
        return limit;
    }

    private static void requireStatus(Card card, String status, String message) {
        if (!status.equals(card.currentStatus())) {
            throw new EfrException(409, message);
        }
    }

    private static void addHistory(Card card, String operation, String login) {
        Map<String, String> record = new LinkedHashMap<>();
        record.put("date", LocalDateTime.ofInstant(Instant.now(), ZoneId.systemDefault()).format(HISTORY_TIME));
        record.put("operation", operation);
        record.put("user", login);
        card.history.add(0, record);
    }

    static String money(long amount) {
        return formatAmount(amount) + " ₽";
    }

    static String formatAmount(long amount) {
        return String.format(Locale.ROOT, "%,d", amount).replace(',', ' ');
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    /** Ошибка бизнес-логики, которую сервер отдаёт клиенту с кодом и текстом. */
    public static final class EfrException extends RuntimeException {
        final int status;

        EfrException(int status, String message) {
            super(message);
            this.status = status;
        }
    }
}
