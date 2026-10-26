package stand;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.BuiltinExchangeType;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/** Подключение к брокеру, топология, публикация событий. */
final class Messaging {

    static final String EXCHANGE = "transfers";
    static final String Q_ACCOUNTING = "accounting.transfer-created";
    static final String Q_NOTIFICATIONS = "notifications.transfer-events";
    static final String Q_DLQ = "transfers.dlq";

    static final JsonMapper JSON = JsonMapper.builder()
            .enable(tools.jackson.databind.DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS)
            .build();

    private final Main.Config cfg;
    private Connection connection;
    private Channel publishChannel;
    private Channel monitorChannel;
    private volatile long accountingDepth;

    Messaging(Main.Config cfg) {
        this.cfg = cfg;
    }

    void start() throws Exception {
        ConnectionFactory f = new ConnectionFactory();
        f.setHost(cfg.str("amqp.host"));
        f.setPort(cfg.integer("amqp.port"));
        f.setUsername(cfg.str("amqp.user"));
        f.setPassword(cfg.str("amqp.password"));
        f.setVirtualHost(cfg.str("amqp.vhost"));
        f.setAutomaticRecoveryEnabled(true);
        connection = f.newConnection("transfer-stand");
        publishChannel = connection.createChannel();
        monitorChannel = connection.createChannel();
        declareTopology(publishChannel);

        ScheduledExecutorService s = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "queue-monitor");
            t.setDaemon(true);
            return t;
        });
        s.scheduleWithFixedDelay(this::refreshDepth, 0, 250, TimeUnit.MILLISECONDS);
        System.out.println("  подключение к брокеру установлено");
    }

    static void declareTopology(Channel ch) throws Exception {
        ch.exchangeDeclare(EXCHANGE, BuiltinExchangeType.TOPIC, true);
        ch.queueDeclare(Q_ACCOUNTING, true, false, false, null);
        ch.queueBind(Q_ACCOUNTING, EXCHANGE, "transfer.created");
        ch.queueDeclare(Q_NOTIFICATIONS, true, false, false, null);
        ch.queueBind(Q_NOTIFICATIONS, EXCHANGE, "transfer.completed");
        ch.queueBind(Q_NOTIFICATIONS, EXCHANGE, "transfer.failed");
        ch.queueDeclare(Q_DLQ, true, false, false, null);
    }

    Channel newChannel() throws Exception {
        return connection.createChannel();
    }

    synchronized void redeclareAndPurge() throws Exception {
        declareTopology(publishChannel);
        publishChannel.queuePurge(Q_ACCOUNTING);
        publishChannel.queuePurge(Q_NOTIFICATIONS);
        publishChannel.queuePurge(Q_DLQ);
    }

    synchronized void publish(String routingKey, JsonNode event) throws Exception {
        AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                .contentType("application/json")
                .contentEncoding("UTF-8")
                .deliveryMode(2)
                .messageId(event.path("eventId").asString(UUID.randomUUID().toString()))
                .type(event.path("eventType").asString(""))
                .build();
        publishChannel.basicPublish(EXCHANGE, routingKey, props, JSON.writeValueAsBytes(event));
    }

    synchronized void toDlq(byte[] body, String sourceQueue, String error) throws Exception {
        AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                .contentType("application/json")
                .deliveryMode(2)
                .headers(Map.of("x-source-queue", sourceQueue, "x-error", error))
                .build();
        publishChannel.basicPublish("", Q_DLQ, props, body);
    }

    private void refreshDepth() {
        try {
            accountingDepth = monitorChannel.messageCount(Q_ACCOUNTING);
        } catch (Exception e) {
            // очередь могли удалить из консоли — вернётся после сброса стенда
        }
    }

    long accountingDepth() {
        return accountingDepth;
    }

    long depth(String queue) {
        try (Channel ch = connection.createChannel()) {
            return ch.messageCount(queue);
        } catch (Exception e) {
            return -1;
        }
    }

    static String utf8(byte[] body) {
        return new String(body, StandardCharsets.UTF_8);
    }
}
