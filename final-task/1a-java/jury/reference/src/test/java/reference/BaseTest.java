package reference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.JsonNode;
import io.restassured.response.Response;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.*;
import reference.support.*;

abstract class BaseTest {
    final StandConfig config = StandConfig.load();
    final ApiClient api = new ApiClient(config);
    final DbProbe db = new DbProbe(config);
    final TestData data = new TestData(api);
    static final Duration WAIT = Duration.ofSeconds(10);
    JsonNode start(TestData.Pair pair, String amount) {
        Response response = api.createTransfer(
                pair.fromNumber(), pair.toNumber(), new BigDecimal(amount), UUID.randomUUID().toString());
        assertEquals(202, response.statusCode(), response.asString());
        JsonNode transfer = api.json(response);
        UUID.fromString(transfer.get("transferId").asText());
        assertEquals("PROCESSING", transfer.get("status").asText());
        return transfer;
    }
    UUID id(JsonNode transfer) {
        return UUID.fromString(transfer.get("transferId").asText());
    }
    JsonNode complete(JsonNode transfer) throws Exception {
        JsonNode done = api.awaitFinal(id(transfer), WAIT);
        assertEquals("COMPLETED", done.get("status").asText(), done.toString());
        return done;
    }
    static void money(String expected, BigDecimal actual) {
        assertThat(actual).isEqualByComparingTo(expected);
    }
    void unchanged(TestData.Pair p) throws Exception {
        money("1000000", api.balance(p.fromNumber()));
        money("1000000", api.balance(p.toNumber()));
        assertEquals(0L,
                ((Number) db.query("SELECT COUNT(*) AS c FROM transfers WHERE from_account=?", p.fromNumber())
                                .get(0)
                                .get("c"))
                        .longValue());
    }
    void clock(String value) {
        api.put("/api/test/clock", api.encode(Map.of("now", value)), 200);
    }
    void pause() {
        api.post("/api/test/consumers/accounting/pause", "{}", 200);
    }
    void resume() {
        api.post("/api/test/consumers/accounting/resume", "{}", 200);
    }
    void closeRecipient(TestData.Pair pair) {
        api.put("/api/test/accounts/" + pair.toNumber() + "/status", "{\"status\":\"CLOSED\"}", 200);
    }
}
