package reference.support;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.*;
import java.util.Map;

/** Снимок глобальных настроек; восстанавливает их и после assertion failure. */
public final class GlobalStandScope implements AutoCloseable {
    private final ApiClient api;
    private final JsonNode clock, consumers;
    private final long entered = System.nanoTime();
    public GlobalStandScope(ApiClient api) {
        this.api = api;
        clock = api.get("/api/test/clock");
        consumers = api.get("/api/test/consumers");
    }
    @Override
    public void close() throws Exception {
        Throwable failure = null;
        for (String consumer : new String[] {"accounting", "notifications"}) {
            try {
                String action = "RUNNING".equals(consumers.get(consumer).asText()) ? "resume" : "pause";
                api.post("/api/test/consumers/" + consumer + "/" + action, "{}", 200);
            } catch (Throwable e) {
                if (failure == null)
                    failure = e;
                else
                    failure.addSuppressed(e);
            }
        }
        try {
            if (clock.get("shifted").asBoolean()) {
                OffsetDateTime restore = OffsetDateTime.parse(clock.get("now").asText())
                                                 .plusNanos(System.nanoTime() - entered);
                api.put("/api/test/clock", api.encode(Map.of("now", restore.toString())), 200);
            } else
                api.delete("/api/test/clock");
        } catch (Throwable e) {
            if (failure == null)
                failure = e;
            else
                failure.addSuppressed(e);
        }
        if (failure instanceof Error error)
            throw error;
        if (failure instanceof Exception exception)
            throw exception;
    }
}
