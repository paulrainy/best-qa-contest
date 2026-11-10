package reference.support;

import java.io.InputStream;
import java.nio.file.*;
import java.util.Properties;

public record StandConfig(String apiUrl, String amqpUri, String dbUrl, String dbUser, String dbPassword) {
    public static StandConfig load() {
        Properties p = new Properties();
        try (InputStream in = StandConfig.class.getResourceAsStream("/stand.properties")) {
            if (in == null)
                throw new IllegalStateException("Нет stand.properties");
            p.load(in);
            String override = System.getProperty("stand.config");
            if (override != null)
                try (InputStream external = Files.newInputStream(Path.of(override))) {
                    p.load(external);
                }
            for (String key : p.stringPropertyNames())
                p.setProperty(key, System.getProperty(key, p.getProperty(key)));
            return new StandConfig(p.getProperty("api.url"), p.getProperty("amqp.uri"),
                    p.getProperty("db.url"), p.getProperty("db.user"), p.getProperty("db.password"));
        } catch (Exception e) {
            throw new IllegalStateException("Настройки стенда", e);
        }
    }
}
