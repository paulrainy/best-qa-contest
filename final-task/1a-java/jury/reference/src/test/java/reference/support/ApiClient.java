package reference.support;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.fasterxml.jackson.databind.*;
import io.restassured.RestAssured;
import io.restassured.builder.RequestSpecBuilder;
import io.restassured.config.*;
import io.restassured.http.Method;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.*;

public final class ApiClient {
    public static final ObjectMapper JSON =
            new ObjectMapper().enable(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS);
    private final RequestSpecification spec;
    public ApiClient(StandConfig config) {
        spec = new RequestSpecBuilder()
                       .setBaseUri(config.apiUrl())
                       .setContentType("application/json")
                       .setConfig(RestAssuredConfig.config().httpClient(HttpClientConfig.httpClientConfig()
                                       .setParam("http.connection.timeout", 5000)
                                       .setParam("http.socket.timeout", 5000)))
                       .build();
    }
    public String encode(Object object) {
        try {
            return JSON.writeValueAsString(object);
        } catch (Exception e) {
            throw new IllegalArgumentException("JSON", e);
        }
    }
    public JsonNode json(Response response) {
        try {
            return JSON.readTree(response.asString());
        } catch (Exception e) {
            throw new AssertionError("Некорректный JSON: " + response.asString(), e);
        }
    }
    public Response request(String method, String path, String body, Map<String, String> headers) {
        var request = RestAssured.given().spec(spec).headers(headers);
        if (body != null)
            request.body(body);
        return request.request(Method.valueOf(method), path);
    }
    public JsonNode call(String method, String path, String body, int expected) {
        Response response = request(method, path, body, Map.of());
        assertEquals(
                expected, response.statusCode(), "HTTP " + method + " " + path + ": " + response.asString());
        return json(response);
    }
    public JsonNode get(String path) {
        return call("GET", path, null, 200);
    }
    public JsonNode post(String path, String body, int expected) {
        return call("POST", path, body, expected);
    }
    public JsonNode put(String path, String body, int expected) {
        return call("PUT", path, body, expected);
    }
    public JsonNode delete(String path) {
        return call("DELETE", path, null, 200);
    }
    public JsonNode createAccount(BigDecimal balance, String clientId, String status) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("balance", balance);
        body.put("status", status);
        if (clientId != null)
            body.put("clientId", clientId);
        return post("/api/test/accounts", encode(body), 201);
    }
    public Response createTransfer(String from, String to, BigDecimal amount, String key) {
        return request("POST", "/api/v1/transfers",
                encode(Map.of("fromAccount", from, "toAccount", to, "amount", amount)),
                key == null ? Map.of() : Map.of("Idempotency-Key", key));
    }
    public JsonNode awaitFinal(UUID id, Duration timeout) throws InterruptedException {
        long until = System.nanoTime() + timeout.toNanos();
        JsonNode last = null;
        do {
            last = get("/api/v1/transfers/" + id);
            if (Set.of("COMPLETED", "FAILED").contains(last.path("status").asText()))
                return last;
            Thread.sleep(25);
        } while (System.nanoTime() < until);
        throw new AssertionError("timeout transferId=" + id + ", last=" + last);
    }
    public BigDecimal balance(String account) {
        return get("/api/v1/accounts/" + account).get("balance").decimalValue();
    }
}
