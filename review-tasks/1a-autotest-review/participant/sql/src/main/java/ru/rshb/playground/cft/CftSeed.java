package ru.rshb.playground.cft;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/**
 * Схема и данные стенда. Данные как на живом стенде: кроме подходящих клиентов и договоров есть
 * умершие клиенты, нерезиденты, заблокированные, исполнительные производства (в том числе ещё не сопоставленные
 * с клиентом), договоры с действующими и закрытыми картами, блокировками и историей операций.
 */
final class CftSeed {

    private static final String[] SCHEMA = {
            "CREATE TABLE \"Z#BRANCH\" (ID BIGINT PRIMARY KEY, C_CODE VARCHAR(10), C_NAME VARCHAR(100), C_OPER_DAY DATE)",
            "CREATE TABLE \"Z#DEPART\" (ID BIGINT PRIMARY KEY, C_CODE VARCHAR(20), C_NAME VARCHAR(100), C_FILIAL VARCHAR(10))",
            "CREATE TABLE \"Z#USER\" (ID BIGINT PRIMARY KEY, C_LOGIN VARCHAR(30), C_NAME VARCHAR(100), C_FILIAL VARCHAR(10), C_DEPART BIGINT)",
            "CREATE TABLE \"Z#USER_ROLE\" (ID BIGINT PRIMARY KEY, C_USER BIGINT, C_ROLE VARCHAR(20))",
            "CREATE TABLE \"Z#CLIENT\" (ID BIGINT PRIMARY KEY, C_NAME VARCHAR(100), C_FILIAL VARCHAR(10), C_IS_RESIDENT CHAR(1))",
            "CREATE TABLE \"Z#CL_PRIV\" (ID BIGINT PRIMARY KEY, C_DOC_DATE_END DATE, C_DEATH_DATE DATE)",
            "CREATE TABLE \"Z#CL_BLOCK\" (ID BIGINT PRIMARY KEY, C_CLIENT BIGINT)",
            "CREATE TABLE \"Z#EXECUTORY_PROCESS\" (ID BIGINT PRIMARY KEY, C_CLIENT BIGINT, C_NUM VARCHAR(40))",
            "CREATE TABLE \"Z#SHB_FORMA_CRS\" (ID BIGINT PRIMARY KEY, C_CLIENT BIGINT, C_CRS_STATUS VARCHAR(20))",
            "CREATE TABLE \"Z#SHB_FORMA_FATCA\" (ID BIGINT PRIMARY KEY, C_CLIENT BIGINT, C_DATE_END DATE)",
            "CREATE TABLE \"Z#COM_STATUS_PRD\" (ID BIGINT PRIMARY KEY, C_CODE VARCHAR(20), C_NAME VARCHAR(100))",
            "CREATE TABLE \"Z#AC_FIN\" (ID BIGINT PRIMARY KEY, C_MAIN_V_ID VARCHAR(20), C_SALDO DECIMAL(17, 2), C_COM_STATUS BIGINT)",
            "CREATE TABLE \"Z#R2_DEPOSIT\" (ID BIGINT PRIMARY KEY, C_NUM_DOG VARCHAR(30), C_CLIENT BIGINT, C_COM_STATUS BIGINT, "
                    + "C_CURRENCY VARCHAR(3), C_FIN_PRODUCT VARCHAR(30), C_FILIAL VARCHAR(10), C_DEPART BIGINT, C_ACCOUNT BIGINT, "
                    + "C_SELLER BIGINT, C_DATE_CREATE DATE, C_DATE_CLOSE DATE)",
            "CREATE TABLE \"Z#R2_DEP_HOLD\" (ID BIGINT PRIMARY KEY, C_DEPOSIT BIGINT, C_KIND VARCHAR(10), C_SUM DECIMAL(17, 2), "
                    + "C_STATE VARCHAR(10), C_DATE_BEGIN DATE, C_REASON VARCHAR(200))",
            "CREATE TABLE \"Z#R2_IP_CARDS\" (ID BIGINT PRIMARY KEY, C_DEPOSIT BIGINT, C_STATE VARCHAR(10))",
            "CREATE TABLE \"Z#MAIN_DOCUM\" (ID BIGINT PRIMARY KEY, C_SUM DECIMAL(17, 2), C_STATE VARCHAR(20), C_CASH_SYMBOL VARCHAR(5))",
            "CREATE TABLE \"Z#R2_FACT_OPER\" (ID BIGINT PRIMARY KEY, C_DEPOSIT BIGINT, C_SUM DECIMAL(17, 2), C_STATE VARCHAR(20), "
                    + "C_DATE DATE, C_MAIN_DOCUM BIGINT)",
    };

    private static final List<String> NAMES_A = List.of(
            "Кузнецов Андрей Викторович", "Соколова Мария Дмитриевна", "Попов Сергей Николаевич",
            "Лебедева Анна Игоревна", "Новиков Дмитрий Алексеевич", "Морозова Елена Сергеевна",
            "Волков Павел Андреевич", "Фёдорова Ольга Владимировна", "Егоров Максим Олегович",
            "Павлова Ирина Юрьевна");
    private static final List<String> NAMES_B = List.of(
            "Семёнов Артём Игоревич", "Голубева Наталья Петровна", "Виноградов Кирилл Ильич");
    private static final List<String> NAMES_EXPIRED = List.of(
            "Богданов Илья Романович", "Воробьёва Дарья Алексеевна", "Фролов Никита Сергеевич",
            "Медведева Ксения Андреевна");

    private final CftDb db;
    private final LocalDate today = LocalDate.now();
    private int accountSeq = 1;
    private int dogSeq = 1;

    private CftSeed(CftDb db) {
        this.db = db;
    }

    static void fill(CftDb db) {
        new CftSeed(db).run();
    }

    private void run() {
        for (String ddl : SCHEMA) {
            db.exec(ddl);
        }
        statuses();

        branch("3400", "Московский РФ", today);
        branch("2600", "Тверской РФ", today);
        branch("1500", "Калужский РФ", today.minusDays(1));

        long msk1 = depart("3400-01", "Доп. офис № 3400/01", "3400");
        long msk2 = depart("3400-02", "Доп. офис № 3400/02", "3400");
        long tver = depart("2600-01", "Доп. офис № 2600/01", "2600");
        long kaluga = depart("1500-01", "Доп. офис № 1500/01", "1500");

        user("petrova_oa", "Петрова Ольга Алексеевна", "3400", msk1, "OPER_FL");
        user("smirnov_dv", "Смирнов Денис Викторович", "3400", msk1, "OPER_FL");
        user("kassir_mn", "Миронова Наталья Сергеевна", "3400", msk1, "CASHIER");
        user("orlova_es", "Орлова Екатерина Сергеевна", "3400", msk2, "OPER_FL");
        user("kassir_ap", "Афанасьев Пётр Ильич", "3400", msk2, "CASHIER");
        user("fedorov_ik", "Фёдоров Игорь Константинович", "2600", tver, "OPER_FL");
        user("kassir_tv", "Тихонова Вера Николаевна", "2600", tver, "CASHIER");
        user("belov_sa", "Белов Станислав Андреевич", "1500", kaluga, "OPER_FL");
        user("kassir_kl", "Климова Любовь Ивановна", "1500", kaluga, "CASHIER");

        // Служебный клиент стенда: на нём тренируются вручную, тесты его не используют
        long ivanov = client("Иванов Иван Иванович", "3400", true, today.plusYears(6), null);
        crs(ivanov);
        fatca(ivanov, null);

        // Подходящие клиенты без формы FATCA
        List<Long> groupA = NAMES_A.stream().map(name -> {
            long id = client(name, "3400", true, today.plusYears(5), null);
            crs(id);
            return id;
        }).toList();

        // Клиенты, у которых есть всё, в том числе действующая форма FATCA
        long b1 = client(NAMES_B.get(0), "3400", true, today.plusYears(4), null);
        crs(b1);
        fatca(b1, null);
        long b2 = client(NAMES_B.get(1), "3400", true, today.plusYears(7), null);
        crs(b2);
        fatca(b2, today.plusYears(1));
        long b3 = client(NAMES_B.get(2), "3400", true, today.plusYears(3), null);
        crs(b3);
        fatca(b3, today.plusYears(2));
        List<Long> groupB = List.of(b1, b2, b3);

        // Срок действия ДУЛ истёк
        int[] expiredDays = {15, 40, 90, 200};
        for (int i = 0; i < NAMES_EXPIRED.size(); i++) {
            long id = client(NAMES_EXPIRED.get(i), "3400", true, today.minusDays(expiredDays[i]), null);
            crs(id);
        }

        // Неподходящие по другим причинам
        long dead = client("Захаров Виктор Павлович", "3400", true, today.plusYears(2), today.minusMonths(3));
        crs(dead);
        long nonResident = client("Ким Александр Вячеславович", "3400", false, today.plusYears(5), null);
        crs(nonResident);
        long blocked = client("Титова Светлана Олеговна", "3400", true, today.plusYears(5), null);
        crs(blocked);
        fatca(blocked, null);
        db.exec("INSERT INTO \"Z#CL_BLOCK\" VALUES (?, ?)", db.nextId(), blocked);
        long debtor = client("Комаров Глеб Евгеньевич", "3400", true, today.plusYears(5), null);
        crs(debtor);
        fatca(debtor, null);
        db.exec("INSERT INTO \"Z#EXECUTORY_PROCESS\" VALUES (?, ?, ?)", db.nextId(), debtor, "45871/26/77001-ИП");
        // Постановление пришло из ФССП, но ещё не сопоставлено с клиентом банка
        db.exec("INSERT INTO \"Z#EXECUTORY_PROCESS\" VALUES (?, NULL, ?)", db.nextId(), "51203/26/77003-ИП");

        long tver1 = client("Смирнова Алла Викторовна", "2600", true, today.plusYears(5), null);
        crs(tver1);
        fatca(tver1, null);
        long tver2 = client("Карпов Олег Дмитриевич", "2600", true, today.plusYears(3), null);
        crs(tver2);
        fatca(tver2, today.plusYears(1));
        long tverExpired = client("Жукова Галина Ивановна", "2600", true, today.minusDays(60), null);
        crs(tverExpired);
        long kaluga1 = client("Гусев Роман Андреевич", "1500", true, today.plusYears(5), null);
        crs(kaluga1);
        fatca(kaluga1, null);

        List<Long> owners = new java.util.ArrayList<>(groupA);
        owners.addAll(groupB);
        int owner = 0;

        // Текущие счета с двумя картами: перевыпущенной (закрыта) и новой (действует)
        for (int i = 0; i < 10; i++) {
            long dep = deposit(owners.get(owner++ % owners.size()), "3400", i % 2 == 0 ? msk1 : msk2, "WORK",
                    "810", "ALL_TEK_ALL_AL", amount(25_000 + i * 12_345), today.minusMonths(14 - i));
            card(dep, "CLOSED");
            card(dep, "ACTIVE");
            history(dep);
            if (i % 3 == 0) {
                hold(dep, "BLOCK", amount(3_000), "CLOSED", today.minusMonths(2), "Блокировка по заявлению клиента");
            }
        }
        // Карта к счёту была, но закрыта
        BigDecimal[] closedCardSaldo = {amount(0), amount(12_400), amount(0), amount(18_950)};
        for (BigDecimal saldo : closedCardSaldo) {
            long dep = deposit(owners.get(owner++ % owners.size()), "3400", msk1, "WORK", "810", "ALL_TEK_ALL_AL",
                    saldo, today.minusMonths(20));
            card(dep, "CLOSED");
            history(dep);
        }
        // Карт к счёту не выпускали
        BigDecimal[] noCardSaldo = {amount(0), amount(31_500), amount(47_200), amount(0)};
        for (BigDecimal saldo : noCardSaldo) {
            long dep = deposit(owners.get(owner++ % owners.size()), "3400", msk2, "WORK", "810", "ALL_TEK_ALL_AL",
                    saldo, today.minusMonths(9));
            history(dep);
        }
        // Счета под арестом
        for (int i = 0; i < 3; i++) {
            long dep = deposit(owners.get(owner++ % owners.size()), "3400", msk1, "WORK", "810", "ALL_TEK_ALL_AL",
                    amount(60_000 + i * 5_000), today.minusMonths(30));
            hold(dep, "ARREST", amount(15_000), "ACTIVE", today.minusDays(20 + i), "Постановление ФССП № 3021" + i + "/26/77001-ИП");
            history(dep);
        }
        // Прочие договоры
        long closed = deposit(groupA.get(0), "3400", msk1, "CLOSE", "810", "ALL_TEK_ALL_AL", amount(0), today.minusYears(3));
        db.exec("UPDATE \"Z#R2_DEPOSIT\" SET C_DATE_CLOSE = ? WHERE ID = ?", today.minusMonths(5), closed);
        deposit(groupA.get(1), "3400", msk2, "WAIT_CONF", "810", "ALL_TEK_ALL_AL", amount(0), today.minusDays(3));
        deposit(groupA.get(2), "3400", msk1, "WORK", "840", "ALL_TEK_ALL_AL", amount(1_200), today.minusMonths(7));
        deposit(groupA.get(3), "3400", msk2, "WORK", "810", "NAK_SCHET", amount(250_000), today.minusMonths(11));

        for (long tverOwner : new long[]{tver1, tver2, tver1}) {
            long dep = deposit(tverOwner, "2600", tver, "WORK", "810", "ALL_TEK_ALL_AL", amount(22_000), today.minusMonths(6));
            history(dep);
        }
        long kalugaDep = deposit(kaluga1, "1500", kaluga, "WORK", "810", "ALL_TEK_ALL_AL", amount(15_000), today.minusMonths(4));
        history(kalugaDep);
    }

    private void statuses() {
        String[][] statuses = {
                {"WAIT_CONF", "Ожидает подтверждения"}, {"WORK", "Работает"}, {"OPEN", "Открыт"}, {"CLOSE", "Закрыт"}};
        for (String[] s : statuses) {
            db.exec("INSERT INTO \"Z#COM_STATUS_PRD\" VALUES (?, ?, ?)", db.statusId(s[0]), s[0], s[1]);
        }
    }

    private void branch(String code, String name, LocalDate operDay) {
        db.exec("INSERT INTO \"Z#BRANCH\" VALUES (?, ?, ?, ?)", db.nextId(), code, name, operDay);
    }

    private long depart(String code, String name, String filial) {
        long id = db.nextId();
        db.exec("INSERT INTO \"Z#DEPART\" VALUES (?, ?, ?, ?)", id, code, name, filial);
        return id;
    }

    private void user(String login, String name, String filial, long depart, String role) {
        long id = db.nextId();
        db.exec("INSERT INTO \"Z#USER\" VALUES (?, ?, ?, ?, ?)", id, login, name, filial, depart);
        db.exec("INSERT INTO \"Z#USER_ROLE\" VALUES (?, ?, ?)", db.nextId(), id, role);
    }

    private long client(String name, String filial, boolean resident, LocalDate docDateEnd, LocalDate deathDate) {
        long id = db.nextId();
        db.exec("INSERT INTO \"Z#CLIENT\" VALUES (?, ?, ?, ?)", id, name, filial, resident ? "1" : "0");
        db.exec("INSERT INTO \"Z#CL_PRIV\" VALUES (?, ?, ?)", id, docDateEnd, deathDate);
        return id;
    }

    private void crs(long client) {
        db.exec("INSERT INTO \"Z#SHB_FORMA_CRS\" VALUES (?, ?, ?)", db.nextId(), client, "NOT_REPORTABLE");
    }

    private void fatca(long client, LocalDate dateEnd) {
        db.exec("INSERT INTO \"Z#SHB_FORMA_FATCA\" VALUES (?, ?, ?)", db.nextId(), client, dateEnd);
    }

    long deposit(long client, String filial, long depart, String status, String currency, String finProduct,
                 BigDecimal saldo, LocalDate created) {
        long account = db.nextId();
        String accountStatus = status.equals("WORK") ? "OPEN" : status;
        db.exec("INSERT INTO \"Z#AC_FIN\" VALUES (?, ?, ?, ?)", account, accountNumber(currency, filial), saldo,
                db.statusId(accountStatus));
        long id = db.nextId();
        db.exec("INSERT INTO \"Z#R2_DEPOSIT\" (ID, C_NUM_DOG, C_CLIENT, C_COM_STATUS, C_CURRENCY, C_FIN_PRODUCT, C_FILIAL, "
                        + "C_DEPART, C_ACCOUNT, C_DATE_CREATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                id, "ТС-%s-%06d".formatted(filial, 4100 + dogSeq++), client, db.statusId(status), currency, finProduct,
                filial, depart, account, created);
        return id;
    }

    private String accountNumber(String currency, String filial) {
        return "40817%s7%s%07d".formatted(currency, filial, 1_204_000 + accountSeq++);
    }

    private void card(long deposit, String state) {
        db.exec("INSERT INTO \"Z#R2_IP_CARDS\" VALUES (?, ?, ?)", db.nextId(), deposit, state);
    }

    private void hold(long deposit, String kind, BigDecimal sum, String state, LocalDate begin, String reason) {
        db.exec("INSERT INTO \"Z#R2_DEP_HOLD\" VALUES (?, ?, ?, ?, ?, ?, ?)", db.nextId(), deposit, kind, sum, state,
                begin, reason);
    }

    /** История операций по договору: два давних взноса наличных, уже проведённых. */
    private void history(long deposit) {
        for (int daysAgo : new int[]{45, 12}) {
            BigDecimal sum = amount(1_000 + daysAgo * 100);
            long doc = db.nextId();
            db.exec("INSERT INTO \"Z#MAIN_DOCUM\" VALUES (?, ?, ?, ?)", doc, sum, "PROV", "16");
            db.exec("INSERT INTO \"Z#R2_FACT_OPER\" VALUES (?, ?, ?, ?, ?, ?)", db.nextId(), deposit, sum, "PERFORMED",
                    today.minusDays(daysAgo), doc);
        }
    }

    private static BigDecimal amount(long rubles) {
        return BigDecimal.valueOf(rubles).setScale(2);
    }
}
