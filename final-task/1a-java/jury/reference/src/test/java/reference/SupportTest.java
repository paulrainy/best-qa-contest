package reference;

import static org.junit.jupiter.api.Assertions.*;

import com.rabbitmq.client.*;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import reference.support.*;

class SupportTest {
    final StandConfig config = StandConfig.load();
    final ApiClient api = new ApiClient(config);
    final TestData data = new TestData(api);

    @Test
    void timeoutNamesTransferAndScopeRestoresAfterException() throws Exception {
        var initialClock = api.get("/api/test/clock");
        var initialConsumers = api.get("/api/test/consumers");
        var pair = data.own();
        AssertionError error = assertThrows(AssertionError.class, () -> {
            try (var scope = new GlobalStandScope(api)) {
                api.post("/api/test/consumers/accounting/pause", "{}", 200);
                api.post("/api/test/consumers/notifications/pause", "{}", 200);
                api.put("/api/test/clock", "{\"now\":\"2027-07-02T12:00:00+03:00\"}", 200);
                var response = api.createTransfer(pair.fromNumber(), pair.toNumber(), new BigDecimal("100"),
                        UUID.randomUUID().toString());
                assertEquals(202, response.statusCode());
                UUID id = UUID.fromString(api.json(response).get("transferId").asText());
                AssertionError timeout =
                        assertThrows(AssertionError.class, () -> api.awaitFinal(id, Duration.ofMillis(150)));
                assertTrue(timeout.getMessage().contains(id.toString()));
                throw new AssertionError("scope test exception");
            }
        });
        assertEquals("scope test exception", error.getMessage());
        assertEquals(initialClock.get("shifted"), api.get("/api/test/clock").get("shifted"));
        assertEquals(initialConsumers, api.get("/api/test/consumers"));
    }
    @Test
    void queueIsBoundBeforeActionAndDeletedOnClose() throws Exception {
        var pair = data.own();
        String queue;
        try (var probe = AmqpProbe.subscribe(config, "transfer.created")) {
            queue = probe.queueName();
            var response = api.createTransfer(
                    pair.fromNumber(), pair.toNumber(), new BigDecimal("100"), UUID.randomUUID().toString());
            assertEquals(202, response.statusCode());
            UUID id = UUID.fromString(api.json(response).get("transferId").asText());
            var event = probe.await(id, "TransferCreated", Duration.ofSeconds(5));
            assertEquals(id.toString(), event.get("transferId").asText());
            assertEquals("COMPLETED", api.awaitFinal(id, Duration.ofSeconds(5)).get("status").asText());
            assertEquals(2, new DbProbe(config).postings(id).size());
        }
        var factory = new ConnectionFactory();
        factory.setUri(config.amqpUri());
        try (var connection = factory.newConnection()) {
            var channel = connection.createChannel();
            assertThrows(java.io.IOException.class, () -> channel.queueDeclarePassive(queue));
            if (channel.isOpen())
                channel.close();
        }
    }
    @Test
    void missingEventHasBoundedTimeoutWithTransferId() throws Exception {
        UUID id = UUID.randomUUID();
        try (var probe = AmqpProbe.subscribe(config, "transfer.created")) {
            AssertionError timeout = assertThrows(
                    AssertionError.class, () -> probe.await(id, "TransferCreated", Duration.ofMillis(150)));
            assertTrue(timeout.getMessage().contains(id.toString()));
        }
    }
}
