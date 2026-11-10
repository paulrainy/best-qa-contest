package stand;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.DefaultConsumer;
import com.rabbitmq.client.Envelope;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Учёт: читает TransferCreated, зачисляет получателю, публикует TransferCompleted / TransferFailed. */
final class AccountingConsumer extends PausableConsumer {

    private final Db db;
    private final StandClock clock;
    private final Metrics metrics;
    private final Map<String, Integer> attempts = new ConcurrentHashMap<>();

    AccountingConsumer(Db db, Messaging mq, StandClock clock, Metrics metrics) {
        super("accounting", Messaging.Q_ACCOUNTING, mq);
        this.db = db;
        this.clock = clock;
        this.metrics = metrics;
    }

    void clearAttempts() {
        attempts.clear();
    }

    @Override
    protected void configure(Channel ch) throws Exception {
        // ДЕФЕКТ Н1: один потребитель, prefetch = 1, синхронная обработка — пропускная способность ~35 сообщений/с
        ch.basicQos(1);
    }

    @Override
    protected void handle(Channel ch, Envelope env, AMQP.BasicProperties props, byte[] body) throws Exception {
        long tag = env.getDeliveryTag();
        JsonNode event;
        try {
            event = Messaging.JSON.readTree(body);
            require(event, "transferId");
            require(event, "toAccount");
            require(event, "fromAccount");
            require(event, "commission");
            require(event, "totalDebited");
            UUID.fromString(event.get("transferId").asString());
        } catch (Exception e) {
            retryOrDlq(ch, tag, body, "Некорректное сообщение: " + e.getMessage());
            return;
        }

        UUID transferId = UUID.fromString(event.get("transferId").asString());
        TransferService.pause(25); // Известное ограничение Н1: один последовательный потребитель.
        try (Connection c = db.connection()) {
            c.setAutoCommit(false);
            try (PreparedStatement ps = c.prepareStatement("SELECT status FROM transfers WHERE transfer_id = ? FOR UPDATE")) {
                ps.setObject(1, transferId);
                try (var rs = ps.executeQuery()) {
                    if (rs.next() && !"PROCESSING".equals(rs.getString(1))) {
                        c.commit(); ch.basicAck(tag, false); return;
                    }
                }
            }
            ObjectNode transfer = TransferService.findById(c, transferId);
            if (transfer == null) {
                c.rollback();
                retryOrDlq(ch, tag, body, "Неизвестный перевод " + transferId);
                return;
            }
            Instant now = clock.now();
            OffsetDateTime at = StandClock.msk(now);
            String to = transfer.get("toAccount").asString();
            String from = transfer.get("fromAccount").asString();
            BigDecimal amount = transfer.get("amount").decimalValue();
            BigDecimal commission = transfer.get("commission").decimalValue();
            TransferService.Account dst = TransferService.load(c, to);

            ObjectNode out = Messaging.JSON.createObjectNode();
            out.put("eventId", UUID.randomUUID().toString());
            out.put("transferId", transferId.toString());
            out.put("fromAccount", from);
            out.put("toAccount", to);
            out.put("amount", amount);
            out.put("commission", commission);
            out.put("currency", "RUB");
            out.put("occurredAt", at.toString());

            if (dst == null || "CLOSED".equals(dst.status())) {
                // Известное отклонение F16: возвращается только сумма перевода, комиссия остаётся списанной
                BigDecimal refund = amount;
                credit(c, from, refund);
                TransferService.posting(c, transferId, from, "CREDIT", "REFUND", refund, at);
                finish(c, transferId, "FAILED", "RECIPIENT_ACCOUNT_CLOSED", at);
                out.put("eventType", "TransferFailed");
                out.put("reason", "RECIPIENT_ACCOUNT_CLOSED");
                out.put("refundedAmount", refund);
                c.commit();
                mq.publish("transfer.failed", out);
                metrics.transfer("failed");
            } else {
                BigDecimal credited = amount;
                credit(c, to, credited);
                TransferService.posting(c, transferId, to, "CREDIT", "AMOUNT", credited, at);
                finish(c, transferId, "COMPLETED", null, at);
                out.put("eventType", "TransferCompleted");
                c.commit();
                mq.publish("transfer.completed", out);
                metrics.transfer("completed");
            }
            OffsetDateTime created = OffsetDateTime.parse(transfer.get("createdAt").asString());
            metrics.completion(Math.max(0, Duration.between(created.toInstant(), now).toMillis() / 1000.0));
            metrics.processedMessage();
            attempts.remove(key(body));
            ch.basicAck(tag, false);
        } catch (Exception e) {
            retryOrDlq(ch, tag, body, "Ошибка обработки: " + e.getMessage());
        }
    }

    private void retryOrDlq(Channel ch, long tag, byte[] body, String error) throws Exception {
        String k = key(body);
        int n = attempts.merge(k, 1, Integer::sum);
        if (n >= 3) {
            attempts.remove(k);
            mq.toDlq(body, Messaging.Q_ACCOUNTING, error);
            ch.basicAck(tag, false);
        } else {
            ch.basicNack(tag, false, true);
        }
    }

    private static String key(byte[] body) {
        return Integer.toHexString(java.util.Arrays.hashCode(body)) + ":" + body.length;
    }

    private static void require(JsonNode n, String field) {
        if (n == null || !n.hasNonNull(field)) {
            throw new IllegalArgumentException("нет поля " + field);
        }
    }

    private static void credit(Connection c, String account, BigDecimal amount) throws Exception {
        try (PreparedStatement ps = c.prepareStatement(
                "UPDATE accounts SET balance = balance + ? WHERE account_number = ?")) {
            ps.setBigDecimal(1, amount);
            ps.setString(2, account);
            ps.executeUpdate();
        }
    }

    private static void finish(Connection c, UUID id, String status, String reason, OffsetDateTime at)
            throws Exception {
        try (PreparedStatement ps = c.prepareStatement(
                "UPDATE transfers SET status = ?, fail_reason = ?, completed_at = ? WHERE transfer_id = ?")) {
            ps.setString(1, status);
            ps.setString(2, reason);
            ps.setObject(3, at);
            ps.setObject(4, id);
            ps.executeUpdate();
        }
    }
}

/** Потребитель, которого тестовый API может приостановить и возобновить. */
abstract class PausableConsumer {

    final String name;
    final String queue;
    final Messaging mq;
    private final Object handling = new Object();
    private Channel channel;
    private volatile String tag;

    PausableConsumer(String name, String queue, Messaging mq) {
        this.name = name;
        this.queue = queue;
        this.mq = mq;
    }

    protected void configure(Channel ch) throws Exception {
        ch.basicQos(10);
    }

    protected abstract void handle(Channel ch, Envelope env, AMQP.BasicProperties props, byte[] body)
            throws Exception;

    synchronized void start() throws Exception {
        if (tag != null) {
            return;
        }
        if (channel == null || !channel.isOpen()) {
            channel = mq.newChannel();
            configure(channel);
        }
        Channel ch = channel;
        tag = ch.basicConsume(queue, false, name, new DefaultConsumer(ch) {
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope, AMQP.BasicProperties properties,
                                       byte[] body) {
                try {
                    synchronized (handling) {
                        if (ch.isOpen()) {
                            handle(ch, envelope, properties, body);
                        }
                    }
                } catch (Exception e) {
                    System.out.println("[" + name + "] " + e);
                }
            }
        });
    }

    synchronized void pause() throws Exception {
        if (tag != null) {
            channel.basicCancel(tag);
            tag = null;
            // дожидаемся текущей обработки; неподтверждённые сообщения вернутся в очередь при закрытии канала
            synchronized (handling) {
                channel.close();
            }
            channel = null;
        }
    }

    boolean running() {
        return tag != null;
    }
}
