package stand;

import java.io.InputStream;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/** Точка входа стенда: брокер, БД, потребители, HTTP API. */
public class Main {

    public static void main(String[] args) throws Exception {
        Config cfg = Config.load();
        System.out.println("Стенд «Переводы» запускается...");

        if (cfg.bool("broker.embedded")) {
            EmbeddedBroker.start(cfg);
        }
        Db db = new Db(cfg);
        db.start();
        db.writeAccountsCsv(cfg.baseDir().resolve("test-data").resolve("accounts.csv"));

        StandClock clock = new StandClock();
        Metrics metrics = new Metrics();
        Messaging mq = new Messaging(cfg);
        mq.start();

        AccountingConsumer accounting = new AccountingConsumer(db, mq, clock, metrics);
        NotificationConsumer notifications = new NotificationConsumer(db, mq, clock);
        accounting.start();
        notifications.start();

        TransferService service = new TransferService(db, mq, clock, metrics);
        Api api = new Api(cfg, db, mq, clock, metrics, service, accounting, notifications);
        api.start();

        System.out.println();
        System.out.println("Стенд готов.");
        System.out.println("  HTTP API:          http://localhost:" + cfg.str("http.port") + "/api/v1/health");
        System.out.println("  Брокер (AMQP):     amqp://" + cfg.str("amqp.user") + ":" + cfg.str("amqp.password")
                + "@" + cfg.str("amqp.host") + ":" + cfg.str("amqp.port") + "/");
        if (cfg.bool("broker.embedded")) {
            System.out.println("  Консоль брокера:   http://localhost:" + cfg.str("broker.console.port")
                    + "/  (логин " + cfg.str("amqp.user") + " / " + cfg.str("amqp.password") + ")");
        }
        System.out.println("  БД (только чтение): jdbc:h2:tcp://localhost:" + cfg.str("db.port") + "/mem:stand"
                + "  (логин " + cfg.str("db.user") + " / " + cfg.str("db.password") + ")");
        System.out.println("  Веб-консоль БД:    http://localhost:" + cfg.str("db.console.port") + "/");
        System.out.println("  Метрики:           http://localhost:" + cfg.str("http.port") + "/metrics");
        System.out.println("Остановить: Ctrl+C");
    }

    /** Настройки: значения по умолчанию из ресурса, поверх — stand.properties рядом с jar. */
    static final class Config {
        private final Properties props;
        private final Path baseDir;

        private Config(Properties props, Path baseDir) {
            this.props = props;
            this.baseDir = baseDir;
        }

        static Config load() throws Exception {
            Properties p = new Properties();
            try (InputStream in = Main.class.getResourceAsStream("/defaults.properties")) {
                p.load(new java.io.InputStreamReader(in, StandardCharsets.UTF_8));
            }
            Path base = jarDir();
            Path file = base.resolve("stand.properties");
            if (!Files.exists(file)) {
                file = Path.of("stand.properties");
            }
            if (Files.exists(file)) {
                try (Reader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
                    Properties user = new Properties();
                    user.load(r);
                    p.putAll(user);
                }
            }
            for (String name : p.stringPropertyNames()) {
                String sys = System.getProperty(name);
                if (sys != null) {
                    p.setProperty(name, sys);
                }
            }
            return new Config(p, base);
        }

        private static Path jarDir() {
            try {
                Path p = Path.of(Main.class.getProtectionDomain().getCodeSource().getLocation().toURI());
                return Files.isDirectory(p) ? Path.of("").toAbsolutePath() : p.getParent();
            } catch (Exception e) {
                return Path.of("").toAbsolutePath();
            }
        }

        String str(String key) {
            return props.getProperty(key).trim();
        }

        int integer(String key) {
            return Integer.parseInt(str(key));
        }

        boolean bool(String key) {
            return Boolean.parseBoolean(str(key));
        }

        Path baseDir() {
            return baseDir;
        }
    }
}
