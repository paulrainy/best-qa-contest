package utils;

import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;

/**
 * Ожидание по условию: проверка повторяется с интервалом, пока не выполнится или не истечёт таймаут.
 */
public final class Timer {

    private final long intervalMs;
    private final long timeoutMs;

    private Timer(long intervalMs, long timeoutMs) {
        this.intervalMs = intervalMs;
        this.timeoutMs = timeoutMs;
    }

    /**
     * Интервал 2 секунды, таймаут 60 секунд.
     */
    public static Timer setDefault() {
        return new Timer(2_000, 60_000);
    }

    /**
     * Свои интервал и таймаут.
     */
    public static Timer set(long interval, long timeout, TimeUnit unit) {
        return new Timer(unit.toMillis(interval), unit.toMillis(timeout));
    }

    public long getTimeoutSeconds() {
        return timeoutMs / 1000;
    }

    /**
     * true, если условие выполнилось до таймаута.
     */
    public boolean waitFor(BooleanSupplier condition) {
        long deadline = System.currentTimeMillis() + timeoutMs;
        while (true) {
            if (condition.getAsBoolean()) {
                return true;
            }
            if (System.currentTimeMillis() + intervalMs > deadline) {
                return false;
            }
            try {
                Thread.sleep(intervalMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
    }
}
