package starter;

import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.GetResponse;
import io.restassured.builder.RequestSpecBuilder;
import io.restassured.http.ContentType;
import io.restassured.specification.RequestSpecification;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.DriverManager;
import java.time.Duration;
import java.time.Instant;
import java.util.Properties;
import java.util.function.Predicate;

/** Подключения к стенду: HTTP API, брокер, БД. Каркас — меняйте как удобно. */
public final class Stand {

    private static final Properties CFG = load();

    private Stand() {
    }

    private static Properties load() {
        Properties p = new Properties();
        try (InputStream in = Stand.class.getResourceAsStream("/stand.properties")) {
            p.load(in);
        } catch (Exception e) {
            throw new IllegalStateException("Нет stand.properties", e);
        }
        return p;
    }

    public static RequestSpecification api() {
        return new RequestSpecBuilder()
                .setBaseUri(CFG.getProperty("api.url"))
                .setContentType(ContentType.JSON)
                .build();
    }

    public static Connection amqp() throws Exception {
        ConnectionFactory f = new ConnectionFactory();
        f.setUri(CFG.getProperty("amqp.uri"));
        return f.newConnection("autotests");
    }

    public static java.sql.Connection db() throws Exception {
        return DriverManager.getConnection(CFG.getProperty("db.url"), CFG.getProperty("db.user"),
                CFG.getProperty("db.password"));
    }

    /**
     * Подписка на события обменника transfers: временная очередь, которая удаляется при закрытии канала.
     * Создавайте её ДО действия, события которого хотите поймать.
     */
    public static String subscribe(Channel ch, String routingKey) throws Exception {
        String q = ch.queueDeclare("", false, true, true, null).getQueue();
        ch.queueBind(q, "transfers", routingKey);
        return q;
    }

    /** Ждёт в очереди сообщение, тело которого удовлетворяет условию. */
    public static String await(Channel ch, String queue, Predicate<String> match, Duration timeout) throws Exception {
        Instant end = Instant.now().plus(timeout);
        while (Instant.now().isBefore(end)) {
            GetResponse r = ch.basicGet(queue, true);
            if (r == null) {
                Thread.sleep(100);
                continue;
            }
            String body = new String(r.getBody(), StandardCharsets.UTF_8);
            if (match.test(body)) {
                return body;
            }
        }
        throw new AssertionError("Сообщение не пришло за " + timeout);
    }
}
