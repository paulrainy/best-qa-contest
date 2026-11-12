package stand;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Envelope;
import tools.jackson.databind.JsonNode;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.Locale;
import java.util.UUID;

/** Уведомления: по TransferCompleted / TransferFailed пишет уведомление отправителю. */
final class NotificationConsumer extends PausableConsumer {

    private final Db db;
    private final StandClock clock;

    NotificationConsumer(Db db, Messaging mq, StandClock clock) {
        super("notifications", Messaging.Q_NOTIFICATIONS, mq);
        this.db = db;
        this.clock = clock;
    }

    @Override
    protected void handle(Channel ch, Envelope env, AMQP.BasicProperties props, byte[] body) throws Exception {
        long tag = env.getDeliveryTag();
        JsonNode e;
        UUID transferId;
        String from;
        String to;
        BigDecimal amount;
        BigDecimal commission;
        try {
            e = Messaging.JSON.readTree(body);
            // Без transferId нельзя отсечь повторную доставку, поэтому такое сообщение некорректно.
            transferId = UUID.fromString(e.get("transferId").asString());
            from = e.get("fromAccount").asString();
            to = e.get("toAccount").asString();
            amount = e.get("amount").decimalValue();
            commission = e.get("commission").decimalValue();
        } catch (Exception ex) {
            retryOrDlq(ch, tag, body, "Некорректное сообщение: " + ex.getMessage());
            return;
        }
        String error = null;
        try (Connection c = db.connection()) {
            boolean duplicate;
            try (PreparedStatement ps = c.prepareStatement("SELECT 1 FROM notifications WHERE transfer_id = ?")) {
                ps.setObject(1, transferId);
                try (ResultSet rs = ps.executeQuery()) {
                    duplicate = rs.next();
                }
            }
            String sender = duplicate ? null : clientOf(c, from);
            if (!duplicate && sender == null) {
                error = "Счёт отправителя не найден";
            } else if (!duplicate) {
                String text = "TransferFailed".equals(e.path("eventType").asString())
                        ? "Перевод " + rub(amount) + " ₽ на счёт " + to + " не выполнен. Средства "
                            + rub(amount.add(commission)) + " ₽ возвращены на счёт " + from + "."
                        : "Перевод " + rub(amount) + " ₽ на счёт " + to + " выполнен. Комиссия " + rub(commission) + " ₽.";
                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO notifications(client_id, transfer_id, text, created_at) VALUES (?, ?, ?, ?)")) {
                    ps.setString(1, sender);
                    ps.setObject(2, transferId);
                    ps.setString(3, text);
                    ps.setObject(4, clock.nowMsk());
                    ps.executeUpdate();
                }
            }
        } catch (Exception ex) {
            // Сбой БД, включая гонку за уникальный индекс: повтор, после третьего подряд — DLQ.
            error = "Ошибка обработки: " + ex.getMessage();
        }
        if (error != null) {
            retryOrDlq(ch, tag, body, error);
            return;
        }
        forgetAttempts(body);
        ch.basicAck(tag, false);
    }

    private static String clientOf(Connection c, String account) throws Exception {
        try (PreparedStatement ps = c.prepareStatement("SELECT client_id FROM accounts WHERE account_number = ?")) {
            ps.setString(1, account);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : null;
            }
        }
    }

    static String rub(BigDecimal v) {
        DecimalFormatSymbols s = new DecimalFormatSymbols(Locale.ROOT);
        s.setGroupingSeparator(' ');
        s.setDecimalSeparator(',');
        DecimalFormat f = new DecimalFormat("#,##0.00", s);
        return f.format(v);
    }
}
