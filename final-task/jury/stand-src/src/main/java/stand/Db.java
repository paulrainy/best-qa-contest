package stand;

import org.h2.jdbcx.JdbcConnectionPool;
import org.h2.tools.Server;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;

/** H2 в памяти. Стенд работает под администратором, участникам выдаётся пользователь только на чтение. */
final class Db {

    static final String DB_NAME = "stand";

    private static final String[] MALE_LAST = {"Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров",
            "Соколов", "Михайлов", "Новиков", "Фёдоров", "Морозов", "Волков", "Алексеев", "Лебедев", "Семёнов",
            "Егоров", "Павлов", "Козлов", "Степанов", "Николаев", "Орлов", "Андреев", "Макаров", "Никитин", "Захаров"};
    private static final String[] MALE_FIRST = {"Александр", "Сергей", "Дмитрий", "Андрей", "Алексей", "Максим",
            "Иван", "Михаил", "Николай", "Владимир", "Павел", "Олег", "Артём", "Евгений", "Роман"};
    private static final String[] FEMALE_FIRST = {"Елена", "Ольга", "Наталья", "Татьяна", "Ирина", "Анна",
            "Мария", "Светлана", "Екатерина", "Марина", "Юлия", "Анастасия", "Дарья", "Софья", "Ксения"};
    private static final String[] FATHER = {"Александров", "Сергеев", "Дмитриев", "Андреев", "Алексеев",
            "Михайлов", "Иванов", "Николаев", "Владимиров", "Павлов", "Петров", "Викторов"};

    private final Main.Config cfg;
    private final String adminPassword = HexFormat.of().formatHex(new SecureRandom().generateSeed(12));
    private JdbcConnectionPool pool;

    Db(Main.Config cfg) {
        this.cfg = cfg;
    }

    void start() throws SQLException {
        pool = JdbcConnectionPool.create("jdbc:h2:mem:" + DB_NAME + ";DB_CLOSE_DELAY=-1", "sa", adminPassword);
        pool.setMaxConnections(64);
        try (Connection c = pool.getConnection(); Statement s = c.createStatement()) {
            s.execute("CREATE USER IF NOT EXISTS " + cfg.str("db.user").toUpperCase()
                    + " PASSWORD '" + cfg.str("db.password").replace("'", "''") + "'");
        }
        reset();
        Server.createTcpServer("-tcpPort", cfg.str("db.port")).start();
        Server.createWebServer("-webPort", cfg.str("db.console.port")).start();
        System.out.println("  БД запущена");
    }

    Connection connection() throws SQLException {
        return pool.getConnection();
    }

    /** Пересоздаёт схему и тестовые данные. */
    synchronized void reset() throws SQLException {
        try (Connection c = pool.getConnection(); Statement s = c.createStatement()) {
            s.execute("DROP TABLE IF EXISTS notifications");
            s.execute("DROP TABLE IF EXISTS postings");
            s.execute("DROP TABLE IF EXISTS transfers");
            s.execute("DROP TABLE IF EXISTS accounts");
            s.execute("DROP TABLE IF EXISTS clients");
            s.execute("DROP SEQUENCE IF EXISTS client_seq");
            s.execute("DROP SEQUENCE IF EXISTS account_seq");
            s.execute("""
                    CREATE TABLE clients (
                      client_id  VARCHAR(10)  PRIMARY KEY,
                      full_name  VARCHAR(200) NOT NULL
                    )""");
            s.execute("""
                    CREATE TABLE accounts (
                      account_number VARCHAR(20)   PRIMARY KEY,
                      client_id      VARCHAR(10)   NOT NULL REFERENCES clients(client_id),
                      currency       VARCHAR(3)    NOT NULL,
                      balance        DECIMAL(19,2) NOT NULL,
                      status         VARCHAR(10)   NOT NULL,
                      opened_at      TIMESTAMP WITH TIME ZONE NOT NULL
                    )""");
            s.execute("""
                    CREATE TABLE transfers (
                      transfer_id     UUID          PRIMARY KEY,
                      idempotency_key VARCHAR(100)  NOT NULL,
                      client_id       VARCHAR(10)   NOT NULL,
                      from_account    VARCHAR(20)   NOT NULL,
                      to_account      VARCHAR(20)   NOT NULL,
                      transfer_type   VARCHAR(5)    NOT NULL,
                      amount          DECIMAL(19,2) NOT NULL,
                      commission      DECIMAL(19,2) NOT NULL,
                      status          VARCHAR(12)   NOT NULL,
                      fail_reason     VARCHAR(50),
                      created_at      TIMESTAMP WITH TIME ZONE NOT NULL,
                      completed_at    TIMESTAMP WITH TIME ZONE
                    )""");
            s.execute("CREATE UNIQUE INDEX transfers_idem ON transfers(idempotency_key)");
            s.execute("""
                    CREATE TABLE postings (
                      posting_id     BIGINT AUTO_INCREMENT PRIMARY KEY,
                      transfer_id    UUID,
                      account_number VARCHAR(20)   NOT NULL,
                      direction      VARCHAR(6)    NOT NULL,
                      posting_type   VARCHAR(12)   NOT NULL,
                      amount         DECIMAL(19,2) NOT NULL,
                      created_at     TIMESTAMP WITH TIME ZONE NOT NULL
                    )""");
            s.execute("CREATE INDEX postings_account ON postings(account_number)");
            s.execute("CREATE INDEX postings_transfer ON postings(transfer_id)");
            s.execute("""
                    CREATE TABLE notifications (
                      notification_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                      client_id       VARCHAR(10) NOT NULL,
                      transfer_id     UUID,
                      text            VARCHAR(1000) NOT NULL,
                      created_at      TIMESTAMP WITH TIME ZONE NOT NULL
                    )""");
            s.execute("CREATE INDEX notifications_client ON notifications(client_id)");
            s.execute("GRANT SELECT ON SCHEMA PUBLIC TO " + cfg.str("db.user").toUpperCase());
            seed(c);
        }
    }

    private void seed(Connection c) throws SQLException {
        int clients = cfg.integer("seed.clients");
        OffsetDateTime opened = OffsetDateTime.parse("2026-01-15T10:00:00+03:00");
        c.setAutoCommit(false);
        try (PreparedStatement pc = c.prepareStatement("INSERT INTO clients VALUES (?, ?)");
             PreparedStatement pa = c.prepareStatement("INSERT INTO accounts VALUES (?, ?, 'RUB', ?, ?, ?)");
             PreparedStatement pp = c.prepareStatement(
                     "INSERT INTO postings(transfer_id, account_number, direction, posting_type, amount, created_at)"
                             + " VALUES (NULL, ?, 'CREDIT', 'OPENING', ?, ?)")) {
            for (int i = 1; i <= clients + 5; i++) {
                String clientId = clientId(i);
                pc.setString(1, clientId);
                pc.setString(2, name(i));
                pc.addBatch();
                String status = i <= clients ? "ACTIVE" : (i % 2 == 0 ? "BLOCKED" : "CLOSED");
                addAccount(pa, pp, accountNumber(i, 1), clientId, new BigDecimal("5000000.00"), "ACTIVE", opened);
                addAccount(pa, pp, accountNumber(i, 2), clientId, new BigDecimal("500000.00"), status, opened);
            }
            pc.executeBatch();
            pa.executeBatch();
            pp.executeBatch();
            c.commit();
        } finally {
            c.setAutoCommit(true);
        }
        seedHistory(c, clients);
        try (Statement s = c.createStatement()) {
            s.execute("CREATE SEQUENCE client_seq START WITH " + (clients + 6));
            s.execute("CREATE SEQUENCE account_seq START WITH " + ((clients + 6) * 10L + 1));
        }
    }

    /** История переводов за прошлые месяцы: завершённые переводы с проводками, остатки пересчитываются. */
    private void seedHistory(Connection c, int clients) throws SQLException {
        int count = cfg.integer("seed.history");
        java.util.Random rnd = new java.util.Random(42);
        OffsetDateTime monthStart = java.time.ZonedDateTime.now(StandClock.MSK).toLocalDate().withDayOfMonth(1)
                .atStartOfDay(StandClock.MSK).toOffsetDateTime();
        c.setAutoCommit(false);
        try (PreparedStatement pt = c.prepareStatement("INSERT INTO transfers(transfer_id, idempotency_key, client_id,"
                + " from_account, to_account, transfer_type, amount, commission, status, created_at, completed_at)"
                + " VALUES (?, ?, ?, ?, ?, ?, ?, 0.00, 'COMPLETED', ?, ?)");
             PreparedStatement pp = c.prepareStatement("INSERT INTO postings(transfer_id, account_number, direction,"
                     + " posting_type, amount, created_at) VALUES (?, ?, ?, 'AMOUNT', ?, ?)")) {
            for (int k = 0; k < count; k++) {
                int src = 1 + rnd.nextInt(clients);
                boolean own = rnd.nextInt(4) == 0;
                int dst = own ? src : 1 + rnd.nextInt(clients);
                if (dst == src && !own) {
                    dst = src % clients + 1;
                }
                String from = accountNumber(src, own ? 1 + rnd.nextInt(2) : 1);
                String to = own ? accountNumber(src, from.endsWith("1") ? 2 : 1) : accountNumber(dst, 1);
                BigDecimal amount = BigDecimal.valueOf(1000 + rnd.nextInt(1_900_000), 2);
                OffsetDateTime created = monthStart.minusSeconds(60 + rnd.nextInt(90 * 24 * 3600));
                OffsetDateTime done = created.plusNanos(150_000_000L + rnd.nextInt(600_000_000));
                java.util.UUID id = new java.util.UUID(rnd.nextLong(), rnd.nextLong());
                pt.setObject(1, id);
                pt.setString(2, "history-" + k);
                pt.setString(3, clientId(src));
                pt.setString(4, from);
                pt.setString(5, to);
                pt.setString(6, own ? "OWN" : "OTHER");
                pt.setBigDecimal(7, amount);
                pt.setObject(8, created);
                pt.setObject(9, done);
                pt.addBatch();
                pp.setObject(1, id);
                pp.setString(2, from);
                pp.setString(3, "DEBIT");
                pp.setBigDecimal(4, amount);
                pp.setObject(5, created);
                pp.addBatch();
                pp.setObject(1, id);
                pp.setString(2, to);
                pp.setString(3, "CREDIT");
                pp.setBigDecimal(4, amount);
                pp.setObject(5, done);
                pp.addBatch();
                if (k % 5000 == 4999) {
                    pt.executeBatch();
                    pp.executeBatch();
                }
            }
            pt.executeBatch();
            pp.executeBatch();
            try (Statement s = c.createStatement()) {
                s.execute("UPDATE accounts a SET balance = (SELECT SUM(CASE WHEN p.direction = 'CREDIT'"
                        + " THEN p.amount ELSE -p.amount END) FROM postings p WHERE p.account_number = a.account_number)");
            }
            c.commit();
        } finally {
            c.setAutoCommit(true);
        }
    }

    private static void addAccount(PreparedStatement pa, PreparedStatement pp, String number, String clientId,
                                   BigDecimal balance, String status, OffsetDateTime opened) throws SQLException {
        pa.setString(1, number);
        pa.setString(2, clientId);
        pa.setBigDecimal(3, balance);
        pa.setString(4, status);
        pa.setObject(5, opened);
        pa.addBatch();
        pp.setString(1, number);
        pp.setBigDecimal(2, balance);
        pp.setObject(3, opened);
        pp.addBatch();
    }

    static String clientId(long i) {
        return String.format("C%05d", i);
    }

    static String accountNumber(long client, int n) {
        return "40817810" + String.format("%012d", client * 10 + n);
    }

    static String name(int i) {
        boolean female = i % 3 == 0;
        String last = MALE_LAST[i % MALE_LAST.length] + (female ? "а" : "");
        String first = female ? FEMALE_FIRST[(i / 3) % FEMALE_FIRST.length] : MALE_FIRST[(i * 7) % MALE_FIRST.length];
        String father = FATHER[(i * 5) % FATHER.length] + (female ? "на" : "ич");
        return last + " " + first + " " + father;
    }

    /** Выгружает список счетов в CSV — для подготовки тестовых данных. */
    void writeAccountsCsv(Path file) {
        try {
            Files.createDirectories(file.getParent());
            Files.writeString(file, accountsCsv(), StandardCharsets.UTF_8);
        } catch (Exception e) {
            System.out.println("  не удалось записать " + file + ": " + e.getMessage());
        }
    }

    String accountsCsv() throws SQLException {
        StringBuilder sb = new StringBuilder("account_number,client_id,status,balance\n");
        try (Connection c = pool.getConnection(); Statement s = c.createStatement();
             ResultSet rs = s.executeQuery(
                     "SELECT account_number, client_id, status, balance FROM accounts ORDER BY account_number")) {
            while (rs.next()) {
                sb.append(rs.getString(1)).append(',').append(rs.getString(2)).append(',')
                        .append(rs.getString(3)).append(',').append(rs.getBigDecimal(4).toPlainString()).append('\n');
            }
        }
        return sb.toString();
    }

    /** Строки таблицы переводов — для отчётов и расчёта лимитов. */
    record TransferRow(String clientId, String type, BigDecimal amount, String status, OffsetDateTime createdAt) {
    }

    List<TransferRow> allTransfers(Connection c) throws SQLException {
        List<TransferRow> list = new ArrayList<>();
        try (Statement s = c.createStatement(); ResultSet rs = s.executeQuery(
                "SELECT client_id, transfer_type, amount, status, created_at, transfer_id, from_account, to_account,"
                        + " idempotency_key FROM transfers")) {
            while (rs.next()) {
                list.add(new TransferRow(rs.getString(1), rs.getString(2), new BigDecimal(rs.getString(3)),
                        rs.getString(4), OffsetDateTime.parse(rs.getString(5).replace(' ', 'T'),
                        java.time.format.DateTimeFormatter.ISO_OFFSET_DATE_TIME)));
            }
        }
        return list;
    }

    long transferRows() {
        try (Connection c = pool.getConnection(); Statement s = c.createStatement();
             ResultSet rs = s.executeQuery("SELECT COUNT(*) FROM transfers")) {
            rs.next();
            return rs.getLong(1);
        } catch (SQLException e) {
            return -1;
        }
    }
}
