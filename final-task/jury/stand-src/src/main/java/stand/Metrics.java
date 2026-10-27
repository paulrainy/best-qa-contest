package stand;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.DoubleAdder;

/** Метрики в текстовом формате Prometheus. */
final class Metrics {

    private static final double[] BUCKETS = {0.25, 0.5, 1, 2, 5, 10, 30, 60};

    private final Map<String, AtomicLong> requests = new ConcurrentHashMap<>();
    private final Map<String, DoubleAdder> durationSum = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> durationCount = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> transfers = new ConcurrentHashMap<>();
    private final AtomicLong[] completion = new AtomicLong[BUCKETS.length + 1];
    private final DoubleAdder completionSum = new DoubleAdder();
    private final AtomicLong processed = new AtomicLong();

    Metrics() {
        for (int i = 0; i < completion.length; i++) {
            completion[i] = new AtomicLong();
        }
    }

    void request(String method, String route, int code, double seconds) {
        requests.computeIfAbsent("method=\"" + method + "\",route=\"" + route + "\",code=\"" + code + "\"",
                k -> new AtomicLong()).incrementAndGet();
        String key = "method=\"" + method + "\",route=\"" + route + "\"";
        durationSum.computeIfAbsent(key, k -> new DoubleAdder()).add(seconds);
        durationCount.computeIfAbsent(key, k -> new AtomicLong()).incrementAndGet();
    }

    void transfer(String outcome) {
        transfers.computeIfAbsent(outcome, k -> new AtomicLong()).incrementAndGet();
    }

    void processedMessage() {
        processed.incrementAndGet();
    }

    void completion(double seconds) {
        completionSum.add(seconds);
        for (int i = 0; i < BUCKETS.length; i++) {
            if (seconds <= BUCKETS[i]) {
                completion[i].incrementAndGet();
            }
        }
        completion[BUCKETS.length].incrementAndGet();
    }

    String render(long accountingDepth, long notificationsDepth, long dlqDepth, long transferRows) {
        StringBuilder sb = new StringBuilder();
        sb.append("# HELP stand_http_requests_total HTTP-запросы к API стенда.\n");
        sb.append("# TYPE stand_http_requests_total counter\n");
        requests.forEach((k, v) -> sb.append("stand_http_requests_total{").append(k).append("} ").append(v).append('\n'));
        sb.append("# HELP stand_http_request_duration_seconds Время обработки HTTP-запросов.\n");
        sb.append("# TYPE stand_http_request_duration_seconds summary\n");
        durationSum.forEach((k, v) -> sb.append("stand_http_request_duration_seconds_sum{").append(k).append("} ")
                .append(v.sum()).append('\n'));
        durationCount.forEach((k, v) -> sb.append("stand_http_request_duration_seconds_count{").append(k)
                .append("} ").append(v).append('\n'));
        sb.append("# HELP stand_transfers_total Переводы по результату обработки.\n");
        sb.append("# TYPE stand_transfers_total counter\n");
        transfers.forEach((k, v) -> sb.append("stand_transfers_total{outcome=\"").append(k).append("\"} ")
                .append(v).append('\n'));
        sb.append("# HELP stand_transfer_completion_seconds Время от создания перевода до финального статуса.\n");
        sb.append("# TYPE stand_transfer_completion_seconds histogram\n");
        for (int i = 0; i < BUCKETS.length; i++) {
            sb.append("stand_transfer_completion_seconds_bucket{le=\"").append(BUCKETS[i]).append("\"} ")
                    .append(completion[i]).append('\n');
        }
        sb.append("stand_transfer_completion_seconds_bucket{le=\"+Inf\"} ").append(completion[BUCKETS.length])
                .append('\n');
        sb.append("stand_transfer_completion_seconds_sum ").append(completionSum.sum()).append('\n');
        sb.append("stand_transfer_completion_seconds_count ").append(completion[BUCKETS.length]).append('\n');
        sb.append("# HELP stand_queue_messages Сообщений в очереди.\n");
        sb.append("# TYPE stand_queue_messages gauge\n");
        sb.append("stand_queue_messages{queue=\"").append(Messaging.Q_ACCOUNTING).append("\"} ")
                .append(accountingDepth).append('\n');
        sb.append("stand_queue_messages{queue=\"").append(Messaging.Q_NOTIFICATIONS).append("\"} ")
                .append(notificationsDepth).append('\n');
        sb.append("stand_queue_messages{queue=\"").append(Messaging.Q_DLQ).append("\"} ")
                .append(dlqDepth).append('\n');
        sb.append("# HELP stand_accounting_messages_processed_total Сообщений, обработанных учётом.\n");
        sb.append("# TYPE stand_accounting_messages_processed_total counter\n");
        sb.append("stand_accounting_messages_processed_total ").append(processed).append('\n');
        sb.append("# HELP stand_db_transfers_rows Строк в таблице transfers.\n");
        sb.append("# TYPE stand_db_transfers_rows gauge\n");
        sb.append("stand_db_transfers_rows ").append(transferRows).append('\n');
        Runtime rt = Runtime.getRuntime();
        sb.append("# HELP jvm_memory_heap_used_bytes Занятая куча JVM.\n");
        sb.append("# TYPE jvm_memory_heap_used_bytes gauge\n");
        sb.append("jvm_memory_heap_used_bytes ").append(rt.totalMemory() - rt.freeMemory()).append('\n');
        sb.append("# HELP jvm_memory_heap_max_bytes Максимум кучи JVM.\n");
        sb.append("# TYPE jvm_memory_heap_max_bytes gauge\n");
        sb.append("jvm_memory_heap_max_bytes ").append(rt.maxMemory()).append('\n');
        sb.append("# HELP process_cpu_load Загрузка CPU процессом стенда (0..1).\n");
        sb.append("# TYPE process_cpu_load gauge\n");
        java.lang.management.OperatingSystemMXBean os = java.lang.management.ManagementFactory.getOperatingSystemMXBean();
        double cpu = os instanceof com.sun.management.OperatingSystemMXBean sun ? sun.getProcessCpuLoad() : -1;
        sb.append("process_cpu_load ").append(cpu).append('\n');
        sb.append("# HELP jvm_threads_live Живых потоков JVM.\n");
        sb.append("# TYPE jvm_threads_live gauge\n");
        sb.append("jvm_threads_live ").append(Thread.activeCount()).append('\n');
        return sb.toString();
    }
}
