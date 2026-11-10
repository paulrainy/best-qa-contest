package reference;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import reference.support.GlobalStandScope;

class IdempotencyTest extends BaseTest {
    @Test
    void sameBodyReturnsOriginalWithoutSecondDebit() throws Exception {
        var p = data.other();
        String key = UUID.randomUUID().toString();
        var first = api.createTransfer(p.fromNumber(), p.toNumber(), new BigDecimal("100"), key);
        assertEquals(202, first.statusCode());
        var t = complete(api.json(first));
        var repeat = api.createTransfer(p.fromNumber(), p.toNumber(), new BigDecimal("100.00"), key);
        assertEquals(200, repeat.statusCode());
        assertEquals(id(t), id(api.json(repeat)));
        money("999900", api.balance(p.fromNumber()));
        money("1000100", api.balance(p.toNumber()));
        assertEquals(2, db.postings(id(t)).size());
        assertEquals(1L,
                ((Number) db.query("SELECT COUNT(*) AS c FROM transfers WHERE idempotency_key=?", key)
                                .get(0)
                                .get("c"))
                        .longValue());
    }
    @Test
    void differentBodyReturns409() throws Exception {
        var p = data.other();
        String key = UUID.randomUUID().toString();
        var first = api.createTransfer(p.fromNumber(), p.toNumber(), new BigDecimal("100"), key);
        assertEquals(202, first.statusCode());
        complete(api.json(first));
        var repeat = api.createTransfer(p.fromNumber(), p.toNumber(), new BigDecimal("200"), key);
        assertEquals(409, repeat.statusCode());
        assertEquals("IDEMPOTENCY_CONFLICT", api.json(repeat).get("code").asText());
        money("999900", api.balance(p.fromNumber()));
        assertEquals(2, db.postings(id(api.json(first))).size());
    }
    @Test
    void keyIsGlobalAcrossClients() throws Exception {
        var p = data.other();
        var another = data.other();
        String key = UUID.randomUUID().toString();
        var first = api.createTransfer(p.fromNumber(), p.toNumber(), new BigDecimal("100"), key);
        assertEquals(202, first.statusCode());
        complete(api.json(first));
        var repeat = api.createTransfer(another.fromNumber(), another.toNumber(), new BigDecimal("100"), key);
        assertEquals(409, repeat.statusCode());
        unchanged(another);
    }
    @Test
    void expiredKeyCreatesNewOperation() throws Exception {
        try (var scope = new GlobalStandScope(api)) {
            clock("2033-01-15T12:00:00+03:00");
            var p = data.other();
            String key = UUID.randomUUID().toString();
            var first = api.createTransfer(p.fromNumber(), p.toNumber(), new BigDecimal("100"), key);
            assertEquals(202, first.statusCode());
            var t = complete(api.json(first));
            clock("2033-01-16T12:00:01+03:00");
            var next = api.createTransfer(p.fromNumber(), p.toNumber(), new BigDecimal("100"), key);
            assertEquals(202, next.statusCode());
            var t2 = complete(api.json(next));
            assertNotEquals(id(t), id(t2));
            money("999800", api.balance(p.fromNumber()));
            assertEquals(2, db.postings(id(t)).size());
            assertEquals(2, db.postings(id(t2)).size());
        }
    }
}
