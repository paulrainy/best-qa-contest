package reference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.*;
import reference.support.GlobalStandScope;

class AsyncTest extends BaseTest {
    @Test
    void processingOnPauseCompletesAfterResume() throws Exception {
        try (var scope = new GlobalStandScope(api)) {
            var p = data.own();
            pause();
            var t = start(p, "100");
            assertEquals("PROCESSING", api.get("/api/v1/transfers/" + id(t)).get("status").asText());
            money("999900", api.balance(p.fromNumber()));
            money("1000000", api.balance(p.toNumber()));
            assertEquals(1, db.postings(id(t)).size());
            resume();
            complete(t);
            money("1000100", api.balance(p.toNumber()));
            assertEquals(2, db.postings(id(t)).size());
        }
    }
    @Test
    void failedTransferRefundsAmountAndCommission() throws Exception {
        try (var scope = new GlobalStandScope(api)) {
            var p = data.other();
            complete(start(p, "100000"));
            var before = api.balance(p.fromNumber());
            pause();
            var t = start(p, "40000");
            money("400", t.get("commission").decimalValue());
            closeRecipient(p);
            resume();
            var failed = api.awaitFinal(id(t), WAIT);
            assertEquals("FAILED", failed.get("status").asText());
            assertEquals("RECIPIENT_ACCOUNT_CLOSED", failed.get("failReason").asText());
            assertThat(api.balance(p.fromNumber())).isEqualByComparingTo(before);
        }
    }
}
