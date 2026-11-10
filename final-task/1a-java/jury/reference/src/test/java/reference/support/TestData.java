package reference.support;

import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;

public final class TestData {
    private final ApiClient api;
    public TestData(ApiClient api) {
        this.api = api;
    }
    public record Pair(JsonNode from, JsonNode to) {
        public String fromNumber() {
            return from.get("accountNumber").asText();
        }
        public String toNumber() {
            return to.get("accountNumber").asText();
        }
        public String clientId() {
            return from.get("clientId").asText();
        }
    }
    public Pair own() {
        return pair(true, "ACTIVE", "ACTIVE");
    }
    public Pair other() {
        return pair(false, "ACTIVE", "ACTIVE");
    }
    public Pair pair(boolean own, String fromStatus, String toStatus) {
        JsonNode from = api.createAccount(new BigDecimal("1000000.00"), null, fromStatus);
        JsonNode to = api.createAccount(
                new BigDecimal("1000000.00"), own ? from.get("clientId").asText() : null, toStatus);
        return new Pair(from, to);
    }
}
