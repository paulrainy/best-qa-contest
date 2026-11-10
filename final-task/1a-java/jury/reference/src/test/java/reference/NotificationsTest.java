package reference;

import static org.awaitility.Awaitility.await;
import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import reference.support.*;

class NotificationsTest extends BaseTest {
    private JsonNode notification(TestData.Pair p, JsonNode t) {
        AtomicReference<JsonNode> found = new AtomicReference<>();
        await().alias("notification transferId=" + id(t)).atMost(WAIT).until(() -> {
            for (var n : api.get("/api/v1/clients/" + p.clientId() + "/notifications"))
                if (n.get("transferId").asText().equals(id(t).toString())) {
                    found.set(n);
                    return true;
                }
            return false;
        });
        return found.get();
    }
    @Test
    void completedNotificationHasCorrectRecipientAndFormat() throws Exception {
        var p = data.other();
        var t = complete(start(p, "1500.50"));
        assertEquals("Перевод 1 500,50 ₽ на счёт " + p.toNumber() + " выполнен. Комиссия 0,00 ₽.",
                notification(p, t).get("text").asText());
        assertTrue(
                api.get("/api/v1/clients/" + p.to().get("clientId").asText() + "/notifications").isEmpty());
    }
    @Test
    void failedNotificationReportsFailure() throws Exception {
        try (var scope = new GlobalStandScope(api)) {
            var p = data.other();
            pause();
            var t = start(p, "1500.50");
            closeRecipient(p);
            resume();
            assertEquals("FAILED", api.awaitFinal(id(t), WAIT).get("status").asText());
            assertEquals("Перевод 1 500,50 ₽ на счёт " + p.toNumber()
                            + " не выполнен. Средства 1 500,50 ₽ возвращены на счёт " + p.fromNumber()
                            + ".",
                    notification(p, t).get("text").asText());
            money("1000000", api.balance(p.fromNumber()));
        }
    }
}
