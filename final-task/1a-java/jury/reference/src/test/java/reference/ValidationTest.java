package reference;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.*;

class ValidationTest extends BaseTest {
    @ParameterizedTest
    @CsvSource({"9.99,400", "10.00,202", "300000.00,202", "300000.01,400", "10.001,400"})
    void amountBoundaries(String amount, int expected) throws Exception {
        var p = data.own();
        var r = api.createTransfer(
                p.fromNumber(), p.toNumber(), new BigDecimal(amount), UUID.randomUUID().toString());
        assertEquals(expected, r.statusCode(), r.asString());
        if (expected == 202) {
            complete(api.json(r));
            money(new BigDecimal("1000000").subtract(new BigDecimal(amount)).toPlainString(),
                    api.balance(p.fromNumber()));
            money(new BigDecimal("1000000").add(new BigDecimal(amount)).toPlainString(),
                    api.balance(p.toNumber()));
        } else {
            assertEquals("VALIDATION_ERROR", api.json(r).get("code").asText());
            unchanged(p);
        }
    }
    @ParameterizedTest
    @ValueSource(strings = {"missingFrom", "missingTo", "missingAmount", "invalidFrom", "invalidTo",
                         "stringAmount", "invalidJson"})
    void invalidPayloadLeavesMoneyUntouched(String variant) throws Exception {
        var p = data.other();
        Map<String, Object> body = new HashMap<>(
                Map.of("fromAccount", p.fromNumber(), "toAccount", p.toNumber(), "amount", 100));
        switch (variant) {
            case "missingFrom" -> body.remove("fromAccount");
            case "missingTo" -> body.remove("toAccount");
            case "missingAmount" -> body.remove("amount");
            case "invalidFrom" -> body.put("fromAccount", "123");
            case "invalidTo" -> body.put("toAccount", 123);
            case "stringAmount" -> body.put("amount", "100");
        }
        var r = api.request("POST", "/api/v1/transfers",
                variant.equals("invalidJson") ? "{" : api.encode(body),
                Map.of("Idempotency-Key", UUID.randomUUID().toString()));
        assertEquals(400, r.statusCode(), r.asString());
        assertEquals("VALIDATION_ERROR", api.json(r).get("code").asText());
        unchanged(p);
    }
    @ParameterizedTest
    @ValueSource(booleans = {true, false})
    void unknownAccountIs404(boolean unknownSender) throws Exception {
        var p = data.other();
        var r = api.createTransfer(unknownSender ? "00000000000000000000" : p.fromNumber(),
                unknownSender ? p.toNumber() : "00000000000000000000", new BigDecimal("100"),
                UUID.randomUUID().toString());
        assertEquals(404, r.statusCode());
        assertEquals("ACCOUNT_NOT_FOUND", api.json(r).get("code").asText());
        unchanged(p);
    }
    @ParameterizedTest
    @ValueSource(booleans = {true, false})
    void invalidKeyIs400(boolean missing) throws Exception {
        var p = data.other();
        var r = api.createTransfer(
                p.fromNumber(), p.toNumber(), new BigDecimal("100"), missing ? null : "x".repeat(101));
        assertEquals(400, r.statusCode());
        assertEquals("VALIDATION_ERROR", api.json(r).get("code").asText());
        unchanged(p);
    }
    @ParameterizedTest
    @CsvSource({"false,ACTIVE,ACTIVE,true", "false,ACTIVE,BLOCKED,true", "false,ACTIVE,CLOSED,false",
            "false,BLOCKED,ACTIVE,false", "false,BLOCKED,BLOCKED,false", "false,BLOCKED,CLOSED,false",
            "false,CLOSED,ACTIVE,false", "false,CLOSED,BLOCKED,false", "false,CLOSED,CLOSED,false",
            "true,ACTIVE,ACTIVE,true", "true,ACTIVE,BLOCKED,true", "true,ACTIVE,CLOSED,false",
            "true,BLOCKED,ACTIVE,false", "true,BLOCKED,BLOCKED,false", "true,BLOCKED,CLOSED,false",
            "true,CLOSED,ACTIVE,false", "true,CLOSED,BLOCKED,false", "true,CLOSED,CLOSED,false"})
    void accountStatusMatrix(boolean own, String sender, String recipient, boolean allowed) throws Exception {
        var p = data.pair(own, sender, recipient);
        var r = api.createTransfer(
                p.fromNumber(), p.toNumber(), new BigDecimal("100"), UUID.randomUUID().toString());
        assertEquals(allowed ? 202 : 422, r.statusCode(), r.asString());
        if (allowed) {
            complete(api.json(r));
            money("999900", api.balance(p.fromNumber()));
            money("1000100", api.balance(p.toNumber()));
        } else {
            String code = api.json(r).get("code").asText();
            if (sender.equals("BLOCKED") && recipient.equals("CLOSED")) {
                // ТЗ не задаёт приоритет причин: применимы и блокировка отправителя, и закрытый получатель.
                assertTrue(Set.of("ACCOUNT_BLOCKED", "ACCOUNT_CLOSED").contains(code), code);
            } else {
                assertEquals(sender.equals("CLOSED") || recipient.equals("CLOSED") ? "ACCOUNT_CLOSED"
                                                                                   : "ACCOUNT_BLOCKED",
                        code);
            }
            unchanged(p);
        }
    }
    @Test
    void selfTransferIsValidationError() throws Exception {
        var p = data.own();
        var r = api.createTransfer(
                p.fromNumber(), p.fromNumber(), new BigDecimal("100"), UUID.randomUUID().toString());
        assertEquals(400, r.statusCode());
        assertEquals("VALIDATION_ERROR", api.json(r).get("code").asText());
        unchanged(p);
    }
}
