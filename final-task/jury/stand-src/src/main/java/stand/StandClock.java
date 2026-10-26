package stand;

import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;

/** Часы стенда. Тестовый API может сдвинуть их; после сдвига время продолжает идти. */
final class StandClock {

    static final ZoneId MSK = ZoneId.of("Europe/Moscow");

    private volatile Duration offset = Duration.ZERO;

    Instant now() {
        return Instant.now().plus(offset);
    }

    OffsetDateTime nowMsk() {
        return now().atZone(MSK).toOffsetDateTime();
    }

    void set(Instant target) {
        offset = Duration.between(Instant.now(), target);
    }

    void reset() {
        offset = Duration.ZERO;
    }

    boolean shifted() {
        return !offset.isZero();
    }

    static OffsetDateTime msk(Instant i) {
        return i.atZone(MSK).toOffsetDateTime();
    }

    static OffsetDateTime utc(Instant i) {
        return i.atOffset(ZoneOffset.UTC);
    }
}
