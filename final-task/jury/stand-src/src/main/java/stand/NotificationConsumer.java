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
        JsonNode e;
        String from;
        String to;
        BigDecimal amount;
        BigDecimal commission;
        try {
            e = Messaging.JSON.readTree(body);
            from = e.get("fromAccount").asString();
            to = e.get("toAccount").asString();
            amount = e.get("amount").decimalValue();
            commission = e.get("commission").decimalValue();
        } catch (Exception ex) {
            mq.toDlq(body, Messaging.Q_NOTIFICATIONS, "Некорректное сообщение: " + ex.getMessage());
            ch.basicAck(env.getDeliveryTag(), false);
            return;
        }
        try (Connection c = db.connection()) {
            String sender = clientOf(c, from);
            String recipientName = nameOf(c, to);
            if (sender == null) {
                mq.toDlq(body, Messaging.Q_NOTIFICATIONS, "Счёт отправителя не найден");
                ch.basicAck(env.getDeliveryTag(), false);
                return;
            }
            // ДЕФЕКТ Р3: для TransferFailed используется шаблон успешного перевода
            String text = "Перевод " + rub(amount) + " ₽ на счёт " + to + " получателю " + recipientName
                    + " выполнен. Комиссия " + rub(commission) + " ₽.";
            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO notifications(client_id, transfer_id, text, created_at) VALUES (?, ?, ?, ?)")) {
                ps.setString(1, sender);
                ps.setObject(2, uuidOrNull(e.path("transferId").asString("")));
                ps.setString(3, text);
                ps.setObject(4, clock.nowMsk());
                ps.executeUpdate();
            }
        }
        ch.basicAck(env.getDeliveryTag(), false);
    }

    private static UUID uuidOrNull(String s) {
        try {
            return UUID.fromString(s);
        } catch (Exception e) {
            return null;
        }
    }

    private static String clientOf(Connection c, String account) throws Exception {
        try (PreparedStatement ps = c.prepareStatement("SELECT client_id FROM accounts WHERE account_number = ?")) {
            ps.setString(1, account);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : null;
            }
        }
    }

    private static String nameOf(Connection c, String account) throws Exception {
        try (PreparedStatement ps = c.prepareStatement("SELECT cl.full_name FROM accounts a JOIN clients cl"
                + " ON cl.client_id = a.client_id WHERE a.account_number = ?")) {
            ps.setString(1, account);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : "";
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
