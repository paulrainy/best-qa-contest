package reference;

import static org.junit.jupiter.api.Assertions.*;

import java.time.LocalDate;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import reference.support.GlobalStandScope;

class TurnoverTest extends BaseTest {
    @Test
    void turnoverIncludesOnlyCompletedOnSelectedMoscowDate() throws Exception {
        try (var scope = new GlobalStandScope(api)) {
            LocalDate day =
                    LocalDate.of(2040, 1, 1)
                            .plusDays(Math.floorMod(UUID.randomUUID().getMostSignificantBits(), 36500));
            boolean unused = false;
            for (int attempt = 0; attempt < 20; attempt++, day = day.plusDays(2)) {
                if (api.get("/api/v1/reports/turnover?date=" + day).get("transfersCount").asInt() == 0
                        && api.get("/api/v1/reports/turnover?date=" + day.plusDays(1))
                                        .get("transfersCount")
                                        .asInt()
                                == 0) {
                    unused = true;
                    break;
                }
            }
            assertTrue(unused, "Не найдены две свободные даты для глобального отчёта");
            clock(day + "T12:00:00+03:00");
            var p = data.other();
            complete(start(p, "100"));
            pause();
            var next = start(p, "200");
            clock(day.plusDays(1) + "T00:01:00+03:00");
            resume();
            complete(next);
            var bad = data.other();
            pause();
            var failed = start(bad, "300");
            closeRecipient(bad);
            resume();
            assertEquals("FAILED", api.awaitFinal(id(failed), WAIT).get("status").asText());
            pause();
            var processing = start(p, "400");
            assertEquals("PROCESSING", api.get("/api/v1/transfers/" + id(processing)).get("status").asText());
            var report = api.get("/api/v1/reports/turnover?date=" + day.plusDays(1));
            assertEquals(1, report.get("transfersCount").asInt());
            money("200", report.get("totalAmount").decimalValue());
            money("0", report.get("totalCommission").decimalValue());
            var previous = api.get("/api/v1/reports/turnover?date=" + day);
            assertEquals(1, previous.get("transfersCount").asInt());
            money("100", previous.get("totalAmount").decimalValue());
            resume();
            complete(processing);
        }
    }
}
