package starter;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.time.Duration;
import java.util.Map;
import java.util.UUID;

import static io.restassured.RestAssured.given;
import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/** Пример: перевод между своими счетами через API, событие в брокере, проводки в БД. */
class SmokeTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    @Test
    void ownTransferIsCompleted() throws Exception {
        // новый клиент с двумя счетами — тестовый API стенда
        String from = given(Stand.api()).body(Map.of("balance", 1000.00))
                .post("/api/test/accounts").then().statusCode(201).extract().path("accountNumber");
        String clientId = given(Stand.api()).get("/api/v1/accounts/" + from).then().extract().path("clientId");
        String to = given(Stand.api()).body(Map.of("clientId", clientId, "balance", 0))
                .post("/api/test/accounts").then().statusCode(201).extract().path("accountNumber");

        try (Connection amqp = Stand.amqp(); Channel ch = amqp.createChannel()) {
            String events = Stand.subscribe(ch, "transfer.#");

            String transferId = given(Stand.api())
                    .header("Idempotency-Key", UUID.randomUUID().toString())
                    .body(Map.of("fromAccount", from, "toAccount", to, "amount", 100.00))
                    .post("/api/v1/transfers")
                    .then().statusCode(202).extract().path("transferId");

            await().atMost(Duration.ofSeconds(10)).until(() -> "COMPLETED".equals(
                    given(Stand.api()).get("/api/v1/transfers/" + transferId).then().extract().path("status")));

            String created = Stand.await(ch, events,
                    b -> b.contains(transferId) && b.contains("TransferCreated"), Duration.ofSeconds(5));
            JsonNode event = JSON.readTree(created);
            assertThat(event.get("amount").decimalValue()).isEqualByComparingTo("100.00");

            try (java.sql.Connection db = Stand.db(); PreparedStatement ps = db.prepareStatement(
                    "SELECT SUM(amount) FROM postings WHERE transfer_id = ? AND direction = 'CREDIT'")) {
                ps.setObject(1, UUID.fromString(transferId));
                try (ResultSet rs = ps.executeQuery()) {
                    rs.next();
                    assertThat(rs.getBigDecimal(1)).isEqualByComparingTo(new BigDecimal("100.00"));
                }
            }
        }
    }
}
