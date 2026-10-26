package stand;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.time.Instant;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** HTTP API стенда: рабочие методы /api/v1, тестовые методы /api/test, метрики /metrics. */
final class Api {

    private static final Pattern TRANSFER = Pattern.compile("/api/v1/transfers/([^/]+)");
    private static final Pattern ACCOUNT = Pattern.compile("/api/v1/accounts/([^/]+)");
    private static final Pattern OPERATIONS = Pattern.compile("/api/v1/accounts/([^/]+)/operations");
    private static final Pattern LIMITS = Pattern.compile("/api/v1/clients/([^/]+)/limits");
    private static final Pattern NOTIFICATIONS = Pattern.compile("/api/v1/clients/([^/]+)/notifications");
    private static final Pattern TEST_STATUS = Pattern.compile("/api/test/accounts/([^/]+)/status");
    private static final Pattern TEST_CONSUMER = Pattern.compile("/api/test/consumers/([^/]+)/(pause|resume)");
    private static final Set<String> STATUSES = Set.of("ACTIVE", "BLOCKED", "CLOSED");

    private final Main.Config cfg;
    private final Db db;
    private final Messaging mq;
    private final StandClock clock;
    private final Metrics metrics;
    private final TransferService service;
    private final AccountingConsumer accounting;
    private final NotificationConsumer notifications;

    Api(Main.Config cfg, Db db, Messaging mq, StandClock clock, Metrics metrics, TransferService service,
        AccountingConsumer accounting, NotificationConsumer notifications) {
        this.cfg = cfg;
        this.db = db;
        this.mq = mq;
        this.clock = clock;
        this.metrics = metrics;
        this.service = service;
        this.accounting = accounting;
        this.notifications = notifications;
    }

    void start() throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress(cfg.integer("http.port")), 256);
        server.createContext("/", this::dispatch);
        server.setExecutor(Executors.newFixedThreadPool(32));
        server.start();
    }

    private record Reply(int status, String contentType, byte[] body, Map<String, String> headers) {
        static Reply json(int status, JsonNode node) {
            return new Reply(status, "application/json; charset=utf-8", Messaging.JSON.writeValueAsBytes(node),
                    Map.of());
        }

        static Reply text(int status, String contentType, String body) {
            return new Reply(status, contentType, body.getBytes(StandardCharsets.UTF_8), Map.of());
        }
    }

    private void dispatch(HttpExchange ex) throws IOException {
        long start = System.nanoTime();
        String method = ex.getRequestMethod();
        String path = ex.getRequestURI().getPath();
        String[] route = {"other"};
        Reply reply;
        try {
            reply = route(ex, method, path, route);
        } catch (ApiError e) {
            reply = Reply.json(e.status, error(e.code, e.getMessage()));
        } catch (tools.jackson.core.JacksonException e) {
            reply = Reply.json(400, error("VALIDATION_ERROR", "Некорректный JSON"));
        } catch (Exception e) {
            reply = Reply.json(500, error("INTERNAL_ERROR", "Внутренняя ошибка стенда"));
            System.out.println("[api] " + method + " " + path + ": " + e);
        }
        reply.headers().forEach((k, v) -> ex.getResponseHeaders().add(k, v));
        ex.getResponseHeaders().add("Content-Type", reply.contentType());
        ex.sendResponseHeaders(reply.status(), reply.body().length == 0 ? -1 : reply.body().length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(reply.body());
        }
        metrics.request(method, route[0], reply.status(), (System.nanoTime() - start) / 1e9);
    }

    private Reply route(HttpExchange ex, String method, String path, String[] route) throws Exception {
        Matcher m;
        if (path.equals("/api/v1/health") && method.equals("GET")) {
            route[0] = "/api/v1/health";
            ObjectNode n = Messaging.JSON.createObjectNode();
            n.put("status", "UP");
            n.put("time", clock.nowMsk().toString());
            n.put("clockShifted", clock.shifted());
            return Reply.json(200, n);
        }
        if (path.equals("/api/v1/transfers") && method.equals("POST")) {
            route[0] = "/api/v1/transfers";
            JsonNode body = readJson(ex);
            TransferService.Result r = service.create(ex.getRequestHeaders().getFirst("Idempotency-Key"), body);
            return Reply.json(r.status(), r.body());
        }
        if ((m = TRANSFER.matcher(path)).matches() && method.equals("GET")) {
            route[0] = "/api/v1/transfers/{id}";
            UUID id;
            try {
                id = UUID.fromString(m.group(1));
            } catch (IllegalArgumentException e) {
                throw new ApiError(404, "TRANSFER_NOT_FOUND", "Перевод " + m.group(1) + " не найден");
            }
            try (Connection c = db.connection()) {
                ObjectNode t = TransferService.findById(c, id);
                if (t == null) {
                    throw new ApiError(404, "TRANSFER_NOT_FOUND", "Перевод " + id + " не найден");
                }
                return Reply.json(200, t);
            }
        }
        if ((m = OPERATIONS.matcher(path)).matches() && method.equals("GET")) {
            route[0] = "/api/v1/accounts/{number}/operations";
            return Reply.json(200, operations(m.group(1)));
        }
        if ((m = ACCOUNT.matcher(path)).matches() && method.equals("GET")) {
            route[0] = "/api/v1/accounts/{number}";
            return Reply.json(200, account(m.group(1)));
        }
        if ((m = LIMITS.matcher(path)).matches() && method.equals("GET")) {
            route[0] = "/api/v1/clients/{id}/limits";
            return Reply.json(200, service.limits(m.group(1)));
        }
        if ((m = NOTIFICATIONS.matcher(path)).matches() && method.equals("GET")) {
            route[0] = "/api/v1/clients/{id}/notifications";
            return Reply.json(200, notificationsOf(m.group(1)));
        }
        if (path.equals("/api/v1/reports/turnover") && method.equals("GET")) {
            route[0] = "/api/v1/reports/turnover";
            return Reply.json(200, turnover(query(ex).get("date")));
        }
        if (path.equals("/metrics") && method.equals("GET")) {
            route[0] = "/metrics";
            return Reply.text(200, "text/plain; version=0.0.4; charset=utf-8",
                    metrics.render(mq.accountingDepth(), mq.depth(Messaging.Q_NOTIFICATIONS),
                            mq.depth(Messaging.Q_DLQ), db.transferRows()));
        }
        if (path.startsWith("/api/test/")) {
            route[0] = "/api/test";
            return test(ex, method, path);
        }
        throw new ApiError(404, "NOT_FOUND", "Метод " + method + " " + path + " не найден");
    }

    private Reply test(HttpExchange ex, String method, String path) throws Exception {
        Matcher m;
        if (path.equals("/api/test/reset") && method.equals("POST")) {
            accounting.pause();
            notifications.pause();
            mq.redeclareAndPurge();
            db.reset();
            clock.reset();
            accounting.clearAttempts();
            accounting.start();
            notifications.start();
            ObjectNode n = Messaging.JSON.createObjectNode();
            n.put("status", "RESET");
            return Reply.json(200, n);
        }
        if (path.equals("/api/test/clock")) {
            if (method.equals("PUT")) {
                JsonNode body = readJson(ex);
                try {
                    clock.set(OffsetDateTime.parse(body.get("now").asString()).toInstant());
                } catch (Exception e) {
                    throw new ApiError(400, "VALIDATION_ERROR",
                            "Ожидается {\"now\": \"2027-03-15T23:59:00+03:00\"}");
                }
            } else if (method.equals("DELETE")) {
                clock.reset();
            } else if (!method.equals("GET")) {
                throw new ApiError(405, "METHOD_NOT_ALLOWED", "Метод не поддерживается");
            }
            ObjectNode n = Messaging.JSON.createObjectNode();
            n.put("now", clock.nowMsk().toString());
            n.put("shifted", clock.shifted());
            return Reply.json(200, n);
        }
        if (path.equals("/api/test/accounts") && method.equals("POST")) {
            return Reply.json(201, createAccount(readJson(ex)));
        }
        if (path.equals("/api/test/accounts.csv") && method.equals("GET")) {
            return Reply.text(200, "text/csv; charset=utf-8", db.accountsCsv());
        }
        if ((m = TEST_STATUS.matcher(path)).matches() && method.equals("PUT")) {
            JsonNode body = readJson(ex);
            String status = body == null ? null : body.path("status").asString(null);
            if (status == null || !STATUSES.contains(status)) {
                throw new ApiError(400, "VALIDATION_ERROR", "status: ACTIVE, BLOCKED или CLOSED");
            }
            try (Connection c = db.connection(); PreparedStatement ps = c.prepareStatement(
                    "UPDATE accounts SET status = ? WHERE account_number = ?")) {
                ps.setString(1, status);
                ps.setString(2, m.group(1));
                if (ps.executeUpdate() == 0) {
                    throw new ApiError(404, "ACCOUNT_NOT_FOUND", "Счёт " + m.group(1) + " не найден");
                }
            }
            return Reply.json(200, account(m.group(1)));
        }
        if (path.equals("/api/test/consumers") && method.equals("GET")) {
            return Reply.json(200, consumers());
        }
        if ((m = TEST_CONSUMER.matcher(path)).matches() && method.equals("POST")) {
            PausableConsumer c = switch (m.group(1)) {
                case "accounting" -> accounting;
                case "notifications" -> notifications;
                default -> throw new ApiError(404, "NOT_FOUND", "Потребитель: accounting или notifications");
            };
            if (m.group(2).equals("pause")) {
                c.pause();
            } else {
                c.start();
            }
            return Reply.json(200, consumers());
        }
        throw new ApiError(404, "NOT_FOUND", "Метод " + method + " " + path + " не найден");
    }

    private ObjectNode consumers() {
        ObjectNode n = Messaging.JSON.createObjectNode();
        n.put("accounting", accounting.running() ? "RUNNING" : "PAUSED");
        n.put("notifications", notifications.running() ? "RUNNING" : "PAUSED");
        return n;
    }

    private ObjectNode createAccount(JsonNode body) throws Exception {
        if (body == null || !body.isObject()) {
            throw new ApiError(400, "VALIDATION_ERROR", "Тело запроса должно быть JSON-объектом");
        }
        String status = body.path("status").asString("ACTIVE");
        if (!STATUSES.contains(status)) {
            throw new ApiError(400, "VALIDATION_ERROR", "status: ACTIVE, BLOCKED или CLOSED");
        }
        BigDecimal balance;
        JsonNode b = body.get("balance");
        if (b == null) {
            balance = new BigDecimal("100000.00");
        } else if (b.isNumber() && b.decimalValue().signum() >= 0 && b.decimalValue().stripTrailingZeros().scale() <= 2) {
            balance = b.decimalValue().setScale(2);
        } else {
            throw new ApiError(400, "VALIDATION_ERROR", "balance — неотрицательное число, не более 2 знаков");
        }
        String clientId = body.path("clientId").asString(null);
        try (Connection c = db.connection()) {
            if (clientId != null) {
                try (PreparedStatement ps = c.prepareStatement("SELECT 1 FROM clients WHERE client_id = ?")) {
                    ps.setString(1, clientId);
                    try (ResultSet rs = ps.executeQuery()) {
                        if (!rs.next()) {
                            throw new ApiError(404, "CLIENT_NOT_FOUND", "Клиент " + clientId + " не найден");
                        }
                    }
                }
            } else {
                long seq;
                try (Statement s = c.createStatement();
                     ResultSet rs = s.executeQuery("SELECT NEXT VALUE FOR client_seq")) {
                    rs.next();
                    seq = rs.getLong(1);
                }
                clientId = Db.clientId(seq);
                String name = body.path("fullName").asString(Db.name((int) seq));
                try (PreparedStatement ps = c.prepareStatement("INSERT INTO clients VALUES (?, ?)")) {
                    ps.setString(1, clientId);
                    ps.setString(2, name);
                    ps.executeUpdate();
                }
            }
            long accSeq;
            try (Statement s = c.createStatement();
                 ResultSet rs = s.executeQuery("SELECT NEXT VALUE FOR account_seq")) {
                rs.next();
                accSeq = rs.getLong(1);
            }
            String number = "40817810" + String.format("%012d", accSeq);
            OffsetDateTime now = clock.nowMsk();
            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO accounts VALUES (?, ?, 'RUB', ?, ?, ?)")) {
                ps.setString(1, number);
                ps.setString(2, clientId);
                ps.setBigDecimal(3, balance);
                ps.setString(4, status);
                ps.setObject(5, now);
                ps.executeUpdate();
            }
            TransferService.posting(c, null, number, "CREDIT", "OPENING", balance, now);
            return account(number);
        }
    }

    private ObjectNode account(String number) throws Exception {
        try (Connection c = db.connection(); PreparedStatement ps = c.prepareStatement(
                "SELECT a.account_number, a.client_id, cl.full_name, a.currency, a.balance, a.status"
                        + " FROM accounts a JOIN clients cl ON cl.client_id = a.client_id WHERE a.account_number = ?")) {
            ps.setString(1, number);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    throw new ApiError(404, "ACCOUNT_NOT_FOUND", "Счёт " + number + " не найден");
                }
                ObjectNode n = Messaging.JSON.createObjectNode();
                n.put("accountNumber", rs.getString(1));
                n.put("clientId", rs.getString(2));
                n.put("ownerName", rs.getString(3));
                n.put("currency", rs.getString(4));
                n.put("balance", rs.getBigDecimal(5));
                n.put("status", rs.getString(6));
                return n;
            }
        }
    }

    private ArrayNode operations(String number) throws Exception {
        account(number);
        ArrayNode list = Messaging.JSON.createArrayNode();
        try (Connection c = db.connection(); PreparedStatement ps = c.prepareStatement(
                "SELECT posting_id, transfer_id, direction, posting_type, amount, created_at FROM postings"
                        + " WHERE account_number = ? ORDER BY posting_id DESC LIMIT 100")) {
            ps.setString(1, number);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    ObjectNode n = list.addObject();
                    n.put("postingId", rs.getLong(1));
                    UUID t = rs.getObject(2, UUID.class);
                    if (t == null) {
                        n.putNull("transferId");
                    } else {
                        n.put("transferId", t.toString());
                    }
                    n.put("direction", rs.getString(3));
                    n.put("type", rs.getString(4));
                    n.put("amount", rs.getBigDecimal(5));
                    n.put("createdAt", TransferService.mskString(rs.getObject(6, OffsetDateTime.class)));
                }
            }
        }
        return list;
    }

    private ArrayNode notificationsOf(String clientId) throws Exception {
        ArrayNode list = Messaging.JSON.createArrayNode();
        try (Connection c = db.connection(); PreparedStatement ps = c.prepareStatement(
                "SELECT notification_id, transfer_id, text, created_at FROM notifications WHERE client_id = ?"
                        + " ORDER BY notification_id DESC LIMIT 100")) {
            ps.setString(1, clientId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    ObjectNode n = list.addObject();
                    n.put("notificationId", rs.getLong(1));
                    UUID t = rs.getObject(2, UUID.class);
                    if (t == null) {
                        n.putNull("transferId");
                    } else {
                        n.put("transferId", t.toString());
                    }
                    n.put("text", rs.getString(3));
                    n.put("createdAt", TransferService.mskString(rs.getObject(4, OffsetDateTime.class)));
                }
            }
        }
        return list;
    }

    private ObjectNode turnover(String date) throws Exception {
        LocalDate day;
        try {
            day = date == null ? clock.nowMsk().toLocalDate() : LocalDate.parse(date);
        } catch (Exception e) {
            throw new ApiError(400, "VALIDATION_ERROR", "date в формате ГГГГ-ММ-ДД");
        }
        // ДЕФЕКТ О5: в оборот попадают переводы во всех финальных статусах, включая FAILED
        String sql = """
                SELECT COUNT(*), COALESCE(SUM(amount), 0), COALESCE(SUM(commission), 0)
                FROM transfers
                WHERE completed_at IS NOT NULL
                  AND CAST((completed_at AT TIME ZONE 'Europe/Moscow') AS DATE) = ?
                """;
        try (Connection c = db.connection(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setObject(1, day);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                ObjectNode n = Messaging.JSON.createObjectNode();
                n.put("date", day.toString());
                n.put("transfersCount", rs.getLong(1));
                n.put("totalAmount", rs.getBigDecimal(2).setScale(2));
                n.put("totalCommission", rs.getBigDecimal(3).setScale(2));
                return n;
            }
        }
    }

    private static JsonNode readJson(HttpExchange ex) throws IOException {
        byte[] bytes = ex.getRequestBody().readAllBytes();
        if (bytes.length == 0) {
            return null;
        }
        return Messaging.JSON.readTree(bytes);
    }

    private static Map<String, String> query(HttpExchange ex) {
        Map<String, String> q = new HashMap<>();
        String raw = ex.getRequestURI().getRawQuery();
        if (raw == null) {
            return q;
        }
        for (String part : raw.split("&")) {
            int i = part.indexOf('=');
            if (i > 0) {
                q.put(URLDecoder.decode(part.substring(0, i), StandardCharsets.UTF_8),
                        URLDecoder.decode(part.substring(i + 1), StandardCharsets.UTF_8));
            }
        }
        return q;
    }

    private static ObjectNode error(String code, String message) {
        ObjectNode n = Messaging.JSON.createObjectNode();
        n.put("code", code);
        n.put("message", message);
        return n;
    }

}
