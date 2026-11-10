package reference;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import reference.support.GlobalStandScope;

class LimitsTest extends BaseTest {
    @ParameterizedTest
    @CsvSource({"149999.99,202", "150000.00,202", "150000.01,422"})
    void dailyLimitBoundaries(String amount, int code) throws Exception {
        try (var scope = new GlobalStandScope(api)) {
            clock("2030-06-20T12:00:00+03:00");
            var p = data.other();
            complete(start(p, "100000"));
            clock("2030-06-21T12:00:00+03:00");
            var r = api.createTransfer(
                    p.fromNumber(), p.toNumber(), new BigDecimal(amount), UUID.randomUUID().toString());
            assertEquals(code, r.statusCode(), r.asString());
            if (code == 202) {
                complete(api.json(r));
                money(amount,
                        api.get("/api/v1/clients/" + p.clientId() + "/limits")
                                .get("dailyUsed")
                                .decimalValue());
                money(new BigDecimal("900000")
                                .subtract(new BigDecimal(amount))
                                .subtract(new BigDecimal("1500"))
                                .toPlainString(),
                        api.balance(p.fromNumber()));
            } else {
                assertEquals("DAILY_LIMIT_EXCEEDED", api.json(r).get("code").asText());
                money("900000", api.balance(p.fromNumber()));
            }
        }
    }
    @Test
    void moscowMidnightResetsDailyLimit() throws Exception {
        try (var scope = new GlobalStandScope(api)) {
            clock("2031-10-15T23:59:00+03:00");
            var p = data.other();
            complete(start(p, "100000"));
            clock("2031-10-16T00:01:00+03:00");
            money("0",
                    api.get("/api/v1/clients/" + p.clientId() + "/limits").get("dailyUsed").decimalValue());
            complete(start(p, "60000"));
            money("60000",
                    api.get("/api/v1/clients/" + p.clientId() + "/limits").get("dailyUsed").decimalValue());
        }
    }
    @Test
    void calendarMonthResetsFreeThreshold() throws Exception {
        try (var scope = new GlobalStandScope(api)) {
            clock("2032-01-31T12:00:00+03:00");
            var p = data.other();
            complete(start(p, "100000"));
            clock("2032-02-01T12:00:00+03:00");
            money("0",
                    api.get("/api/v1/clients/" + p.clientId() + "/limits").get("monthUsed").decimalValue());
            money("0", complete(start(p, "100")).get("commission").decimalValue());
        }
    }
    @Test
    void failedTransferReleasesUsage() throws Exception {
        try (var scope = new GlobalStandScope(api)) {
            var p = data.other();
            pause();
            var t = start(p, "100");
            money("100",
                    api.get("/api/v1/clients/" + p.clientId() + "/limits").get("dailyUsed").decimalValue());
            closeRecipient(p);
            resume();
            assertEquals("FAILED", api.awaitFinal(id(t), WAIT).get("status").asText());
            var usage = api.get("/api/v1/clients/" + p.clientId() + "/limits");
            money("0", usage.get("dailyUsed").decimalValue());
            money("0", usage.get("monthUsed").decimalValue());
            money("1000000", api.balance(p.fromNumber()));
        }
    }
}
