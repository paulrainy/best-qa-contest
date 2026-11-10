package reference.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.rabbitmq.client.*;
import java.time.Duration;
import java.util.UUID;

public final class AmqpProbe implements AutoCloseable {
    private final Connection connection;
    private final Channel channel;
    private final String queue;
    private AmqpProbe(StandConfig config, String key) throws Exception {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setUri(config.amqpUri());
        factory.setConnectionTimeout(5000);
        factory.setHandshakeTimeout(5000);
        factory.setAutomaticRecoveryEnabled(false);
        connection = factory.newConnection("jury-reference");
        Channel ch = null;
        try {
            ch = connection.createChannel();
            queue = ch.queueDeclare("", false, true, true, null).getQueue();
            ch.queueBind(queue, "transfers", key);
            channel = ch;
        } catch (Exception e) {
            connection.close();
            throw e;
        }
    }
    public static AmqpProbe subscribe(String key) throws Exception {
        return subscribe(StandConfig.load(), key);
    }
    public static AmqpProbe subscribe(StandConfig config, String key) throws Exception {
        return new AmqpProbe(config, key);
    }
    public String queueName() {
        return queue;
    }
    public JsonNode await(UUID id, String type, Duration timeout) throws Exception {
        long until = System.nanoTime() + timeout.toNanos();
        do {
            GetResponse response = channel.basicGet(queue, true);
            if (response != null) {
                JsonNode event = ApiClient.JSON.readTree(response.getBody());
                if (id.toString().equals(event.path("transferId").asText())
                        && type.equals(event.path("eventType").asText()))
                    return event;
            } else
                Thread.sleep(25);
        } while (System.nanoTime() < until);
        throw new AssertionError(
                "AMQP timeout transferId=" + id + ", eventType=" + type + ", queue=" + queue);
    }
    @Override
    public void close() throws Exception {
        try {
            if (channel.isOpen()) {
                try {
                    channel.queueDelete(queue);
                } finally {
                    channel.close();
                }
            }
        } finally {
            if (connection.isOpen())
                connection.close();
        }
    }
}
