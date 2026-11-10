package reference;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import reference.support.AmqpProbe;

class EventsTest extends BaseTest {
    @Test
    void createdEventAndPostingsMatchOwnTransfer() throws Exception {
        var p = data.other();
        try (var probe = AmqpProbe.subscribe("transfer.created")) {
            var t = start(p, "100.01");
            var event = probe.await(id(t), "TransferCreated", WAIT);
            complete(t);
            UUID.fromString(event.get("eventId").asText());
            OffsetDateTime.parse(event.get("occurredAt").asText());
            assertEquals("OTHER", event.get("transferType").asText());
            assertEquals(p.fromNumber(), event.get("fromAccount").asText());
            assertEquals(p.toNumber(), event.get("toAccount").asText());
            assertEquals("RUB", event.get("currency").asText());
            money("100.01", event.get("amount").decimalValue());
            money("0", event.get("commission").decimalValue());
            money("100.01", event.get("totalDebited").decimalValue());
            var postings = db.postings(id(t));
            assertEquals(2, postings.size());
            var debit = postings.stream()
                                .filter(r -> r.get("direction").equals("DEBIT"))
                                .findFirst()
                                .orElseThrow();
            var credit = postings.stream()
                                 .filter(r -> r.get("direction").equals("CREDIT"))
                                 .findFirst()
                                 .orElseThrow();
            assertEquals(p.fromNumber(), debit.get("account_number"));
            assertEquals(p.toNumber(), credit.get("account_number"));
            for (var posting : postings) {
                assertEquals("AMOUNT", posting.get("posting_type"));
                money("100.01", (BigDecimal) posting.get("amount"));
            }
        }
    }
}
