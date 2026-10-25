package ru.rshb.playground.cft;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import static ru.rshb.playground.cft.CftDb.asDate;
import static ru.rshb.playground.cft.CftDb.asDecimal;
import static ru.rshb.playground.cft.CftDb.asLong;

/**
 * Операции ЦФТ над базой одного стенда. Проверки — как в настоящем ЦФТ: при нарушении операция
 * возвращает ошибку и ничего не меняет.
 */
final class CftBank {

    /** Через сколько фоновое задание проводит принятый кассиром документ. */
    static final long POSTING_DELAY_MS = 3_000;

    private static final ScheduledExecutorService BACKGROUND = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "cft-posting");
        t.setDaemon(true);
        return t;
    });

    private final CftDb db;

    CftBank(CftDb db) {
        this.db = db;
    }

    /** Пользователь ЦФТ, под которым выполняется операция. */
    record User(long id, String login, String name, String filial, long depart, String role, LocalDate operDay) {
    }

    User login(String login, String password) {
        if (!Stand.PASSWORD.equals(password)) {
            throw new CftException("Неверный логин или пароль");
        }
        Map<String, Object> row = db.row("SELECT u.ID, u.C_LOGIN, u.C_NAME, u.C_FILIAL, u.C_DEPART, r.C_ROLE, b.C_OPER_DAY "
                        + "FROM \"Z#USER\" u JOIN \"Z#USER_ROLE\" r ON r.C_USER = u.ID "
                        + "JOIN \"Z#BRANCH\" b ON b.C_CODE = u.C_FILIAL WHERE u.C_LOGIN = ?", login)
                .orElseThrow(() -> new CftException("Неверный логин или пароль"));
        return new User(asLong(row.get("ID")), (String) row.get("C_LOGIN"), (String) row.get("C_NAME"),
                (String) row.get("C_FILIAL"), asLong(row.get("C_DEPART")), (String) row.get("C_ROLE"),
                asDate(row.get("C_OPER_DAY")));
    }

    // ---------- Открыть новый договор ----------

    synchronized long openDeposit(User user, Long clientId, String finProduct, String currency, Long sellerId) {
        requireRole(user, "OPER_FL");
        if (clientId == null) {
            throw new CftException("Не указан клиент");
        }
        Map<String, Object> client = db.row("SELECT c.ID, c.C_FILIAL, cp.C_DOC_DATE_END, cp.C_DEATH_DATE "
                        + "FROM \"Z#CLIENT\" c JOIN \"Z#CL_PRIV\" cp ON cp.ID = c.ID WHERE c.ID = ?", clientId)
                .orElseThrow(() -> new CftException("Клиент ФЛ с ID %d не найден".formatted(clientId)));
        if (finProduct == null) {
            throw new CftException("Не указан финансовый продукт");
        }
        if (currency == null) {
            throw new CftException("Не указана валюта договора");
        }
        if (client.get("C_DEATH_DATE") != null) {
            throw new CftException("Клиент умер. Открытие договора невозможно");
        }
        LocalDate docEnd = asDate(client.get("C_DOC_DATE_END"));
        if (docEnd == null || docEnd.isBefore(user.operDay())) {
            throw new CftException("Срок действия документа, удостоверяющего личность, истёк");
        }
        if (db.count("SELECT COUNT(*) FROM \"Z#CL_BLOCK\" WHERE C_CLIENT = ?", clientId) > 0) {
            throw new CftException("На клиента наложена блокировка");
        }
        if (db.count("SELECT COUNT(*) FROM \"Z#EXECUTORY_PROCESS\" WHERE C_CLIENT = ?", clientId) > 0) {
            throw new CftException("По клиенту есть исполнительное производство");
        }
        if (db.count("SELECT COUNT(*) FROM \"Z#SHB_FORMA_CRS\" WHERE C_CLIENT = ? AND C_CRS_STATUS IS NOT NULL", clientId) == 0) {
            throw new CftException("Не заполнена форма CRS");
        }
        if (db.count("SELECT COUNT(*) FROM \"Z#SHB_FORMA_FATCA\" WHERE C_CLIENT = ? "
                + "AND (C_DATE_END IS NULL OR C_DATE_END >= ?)", clientId, user.operDay()) == 0) {
            throw new CftException("У клиента нет действующей формы FATCA");
        }
        if (sellerId == null) {
            throw new CftException("На вкладке «Характеристики договора» не указан продавец");
        }

        String filial = (String) client.get("C_FILIAL");
        long account = db.nextId();
        db.exec("INSERT INTO \"Z#AC_FIN\" VALUES (?, ?, ?, ?)", account,
                "40817%s7%s%07d".formatted(currency, filial, account), BigDecimal.ZERO.setScale(2),
                db.statusId("WAIT_CONF"));
        long id = db.nextId();
        db.exec("INSERT INTO \"Z#R2_DEPOSIT\" (ID, C_NUM_DOG, C_CLIENT, C_COM_STATUS, C_CURRENCY, C_FIN_PRODUCT, C_FILIAL, "
                        + "C_DEPART, C_ACCOUNT, C_SELLER, C_DATE_CREATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                id, "ТС-%s-%06d".formatted(filial, id), clientId, db.statusId("WAIT_CONF"), currency, finProduct,
                filial, user.depart(), account, sellerId, user.operDay());
        return id;
    }

    // ---------- Подписать договор ----------

    synchronized void signDeposit(User user, long depositId) {
        requireRole(user, "OPER_FL");
        Map<String, Object> deposit = deposit(depositId);
        requireStatus(deposit, "WAIT_CONF", "Подписать можно только договор в состоянии «Ожидает подтверждения»");
        db.exec("UPDATE \"Z#R2_DEPOSIT\" SET C_COM_STATUS = ? WHERE ID = ?", db.statusId("WORK"), depositId);
        db.exec("UPDATE \"Z#AC_FIN\" SET C_COM_STATUS = ? WHERE ID = ?", db.statusId("OPEN"), deposit.get("C_ACCOUNT"));
    }

    // ---------- Приходная кассовая операция ----------

    synchronized long incomingCash(User user, long depositId, BigDecimal amount, String cashSymbol) {
        requireRole(user, "OPER_FL");
        Map<String, Object> deposit = deposit(depositId);
        requireStatus(deposit, "WORK", "Операция доступна только по договору в состоянии «Работает»");
        if (amount == null || amount.signum() <= 0) {
            throw new CftException("Укажите сумму к зачислению");
        }
        if (cashSymbol == null) {
            throw new CftException("Укажите символ кассы");
        }
        long doc = db.nextId();
        db.exec("INSERT INTO \"Z#MAIN_DOCUM\" VALUES (?, ?, ?, ?)", doc, amount, "TO_KASSA", cashSymbol);
        long factOper = db.nextId();
        db.exec("INSERT INTO \"Z#R2_FACT_OPER\" VALUES (?, ?, ?, ?, ?, ?)", factOper, depositId, amount, "ADD_CONTROL",
                user.operDay(), doc);
        return factOper;
    }

    // ---------- Приём документа кассиром ----------

    synchronized void receiptByCashier(User user, long docId, BigDecimal sum, boolean wiring) {
        requireRole(user, "CASHIER");
        Map<String, Object> doc = db.row("SELECT * FROM \"Z#MAIN_DOCUM\" WHERE ID = ?", docId)
                .orElseThrow(() -> new CftException("Документ с ID %d не найден".formatted(docId)));
        if (!"TO_KASSA".equals(doc.get("C_STATE"))) {
            throw new CftException("Документ не ожидает приёма в кассу");
        }
        if (sum == null || asDecimal(doc.get("C_SUM")).compareTo(sum) != 0) {
            throw new CftException("Сумма не совпадает с суммой документа");
        }
        if (!wiring) {
            throw new CftException("Отметьте «Проводка»");
        }
        db.exec("UPDATE \"Z#MAIN_DOCUM\" SET C_STATE = ? WHERE ID = ?", "IN_KASSA", docId);
        // Проводку выполняет фоновое задание
        BACKGROUND.schedule(() -> post(docId), POSTING_DELAY_MS, TimeUnit.MILLISECONDS);
    }

    private synchronized void post(long docId) {
        Map<String, Object> factOper = db.row("SELECT * FROM \"Z#R2_FACT_OPER\" WHERE C_MAIN_DOCUM = ?", docId).orElseThrow();
        Map<String, Object> deposit = deposit(asLong(factOper.get("C_DEPOSIT")));
        db.exec("UPDATE \"Z#AC_FIN\" SET C_SALDO = C_SALDO + ? WHERE ID = ?", factOper.get("C_SUM"), deposit.get("C_ACCOUNT"));
        db.exec("UPDATE \"Z#MAIN_DOCUM\" SET C_STATE = ? WHERE ID = ?", "PROV", docId);
        db.exec("UPDATE \"Z#R2_FACT_OPER\" SET C_STATE = ? WHERE ID = ?", "PERFORMED", factOper.get("ID"));
    }

    // ---------- Добавить блокировку ----------

    synchronized long addHold(User user, long depositId, String kind, BigDecimal sum, String reason) {
        requireRole(user, "OPER_FL");
        Map<String, Object> deposit = deposit(depositId);
        requireStatus(deposit, "WORK", "Блокировку можно добавить только по договору в состоянии «Работает»");
        if (kind == null) {
            throw new CftException("Укажите вид блокировки");
        }
        if (sum == null || sum.signum() <= 0) {
            throw new CftException("Укажите сумму блокировки");
        }
        if (reason == null || reason.isBlank()) {
            throw new CftException("Укажите основание блокировки");
        }
        long id = db.nextId();
        db.exec("INSERT INTO \"Z#R2_DEP_HOLD\" VALUES (?, ?, ?, ?, ?, ?, ?)", id, depositId, kind, sum, "ACTIVE",
                user.operDay(), reason);
        return id;
    }

    // ---------- Закрыть договор ----------

    synchronized void closeDeposit(User user, long depositId) {
        requireRole(user, "OPER_FL");
        Map<String, Object> deposit = deposit(depositId);
        requireStatus(deposit, "WORK", "Закрыть можно только договор в состоянии «Работает»");
        BigDecimal saldo = asDecimal(db.row("SELECT C_SALDO FROM \"Z#AC_FIN\" WHERE ID = ?", deposit.get("C_ACCOUNT"))
                .orElseThrow().get("C_SALDO"));
        if (saldo.signum() != 0) {
            throw new CftException("Остаток на счёте договора не равен нулю");
        }
        if (db.count("SELECT COUNT(*) FROM \"Z#R2_DEP_HOLD\" WHERE C_DEPOSIT = ? AND C_STATE = 'ACTIVE'", depositId) > 0) {
            throw new CftException("По договору есть действующие блокировки");
        }
        if (db.count("SELECT COUNT(*) FROM \"Z#R2_IP_CARDS\" WHERE C_DEPOSIT = ? AND C_STATE = 'ACTIVE'", depositId) > 0) {
            throw new CftException("По договору есть действующие карты. Закройте их перед закрытием договора");
        }
        db.exec("UPDATE \"Z#R2_DEPOSIT\" SET C_COM_STATUS = ?, C_DATE_CLOSE = ? WHERE ID = ?", db.statusId("CLOSE"),
                user.operDay(), depositId);
        db.exec("UPDATE \"Z#AC_FIN\" SET C_COM_STATUS = ? WHERE ID = ?", db.statusId("CLOSE"), deposit.get("C_ACCOUNT"));
    }

    // ---------- Вспомогательное ----------

    Map<String, Object> describeDeposit(long depositId) {
        Map<String, Object> deposit = deposit(depositId);
        Map<String, Object> json = new LinkedHashMap<>();
        json.put("id", depositId);
        json.put("numDog", deposit.get("C_NUM_DOG"));
        json.put("status", statusCode(asLong(deposit.get("C_COM_STATUS"))));
        return json;
    }

    private Map<String, Object> deposit(long depositId) {
        return db.row("SELECT * FROM \"Z#R2_DEPOSIT\" WHERE ID = ?", depositId)
                .orElseThrow(() -> new CftException("Договор с ID %d не найден".formatted(depositId)));
    }

    private void requireStatus(Map<String, Object> deposit, String code, String message) {
        if (!code.equals(statusCode(asLong(deposit.get("C_COM_STATUS"))))) {
            throw new CftException(message);
        }
    }

    private String statusCode(Long statusId) {
        return db.row("SELECT C_CODE FROM \"Z#COM_STATUS_PRD\" WHERE ID = ?", statusId)
                .map(r -> (String) r.get("C_CODE")).orElse("?");
    }

    private static void requireRole(User user, String role) {
        if (!role.equals(user.role())) {
            throw new CftException("У пользователя %s нет прав на эту операцию".formatted(user.login()));
        }
    }

    /** Ошибка ЦФТ, которую операция показывает пользователю. */
    static final class CftException extends RuntimeException {
        CftException(String message) {
            super(message);
        }
    }
}
