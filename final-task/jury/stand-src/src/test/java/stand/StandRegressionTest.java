package stand;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import java.net.URI;
import java.net.http.*;
import java.sql.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

/** Регресс снимаемых дефектов: реальные HTTP, H2 и встроенный брокер. */
class StandRegressionTest {
    static Db db;
    static Messaging mq;
    static AccountingConsumer accounting;
    static StandClock clock;
    static TransferService service;
    static HttpClient http = HttpClient.newHttpClient();
    static final String BASE = "http://localhost:18410";

    @BeforeAll
    static void start() throws Exception {
        Map.of("http.port", "18410", "amqp.port", "5682", "broker.console.port", "15682", "db.port", "19410",
                   "db.console.port", "19411", "db.pg.port", "19412", "seed.clients", "20", "seed.history",
                   "100")
                .forEach(System::setProperty);
        Main.Config cfg = Main.Config.load();
        EmbeddedBroker.start(cfg);
        db = new Db(cfg);
        db.start();
        clock = new StandClock();
        Metrics metrics = new Metrics();
        mq = new Messaging(cfg);
        mq.start();
        accounting = new AccountingConsumer(db, mq, clock, metrics);
        accounting.start();
        NotificationConsumer notifications = new NotificationConsumer(db, mq, clock);
        notifications.start();
        service = new TransferService(db, mq, clock, metrics);
        new Api(cfg, db, mq, clock, metrics, service, accounting, notifications).start();
    }
    @BeforeEach
    void reset() throws Exception {
        request("POST", "/api/test/reset", "{}");
        long until = System.nanoTime() + Duration.ofSeconds(3).toNanos();
        while (mq.accountingDepth() != 0 && System.nanoTime() < until) Thread.sleep(20);
        assertEquals(0, mq.accountingDepth());
    }
    static HttpResponse<String> request(String method, String path, String body) throws Exception {
        return http.send(HttpRequest.newBuilder(URI.create(BASE + path))
                                 .timeout(Duration.ofSeconds(10))
                                 .header("Content-Type", "application/json")
                                 .header("Idempotency-Key", UUID.randomUUID().toString())
                                 .method(method, HttpRequest.BodyPublishers.ofString(body))
                                 .build(),
                HttpResponse.BodyHandlers.ofString());
    }
    static JsonNode json(HttpResponse<String> r) {
        return Messaging.JSON.readTree(r.body());
    }
    static JsonNode account(String client, String status) throws Exception {
        return json(request("POST", "/api/test/accounts",
                "{\"balance\":1000000,\"status\":\"" + status + "\""
                        + (client == null ? "" : ",\"clientId\":\"" + client + "\"") + "}"));
    }
    static ObjectNode body(JsonNode a, JsonNode b, String amount) {
        ObjectNode n = Messaging.JSON.createObjectNode();
        n.put("fromAccount", a.get("accountNumber").asString());
        n.put("toAccount", b.get("accountNumber").asString());
        n.put("amount", new BigDecimal(amount));
        return n;
    }
    static JsonNode create(JsonNode a, JsonNode b, String amount) throws Exception {
        return service.create(UUID.randomUUID().toString(), body(a, b, amount)).body();
    }
    static JsonNode done(JsonNode t) throws Exception {
        long until = System.nanoTime() + Duration.ofSeconds(8).toNanos();
        JsonNode n;
        do {
            n = json(request("GET", "/api/v1/transfers/" + t.get("transferId").asString(), ""));
            if (!n.path("status").asString().equals("PROCESSING"))
                return n;
            Thread.sleep(20);
        } while (System.nanoTime() < until);
        throw new AssertionError("timeout " + t);
    }
    static void money(String expected, BigDecimal actual) {
        assertEquals(0, new BigDecimal(expected).compareTo(actual));
    }
    @Test
    void dailyBoundaryIsInclusive() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE");
        assertEquals("COMPLETED", done(create(a, b, "150000")).get("status").asString());
    }
    @Test
    void roundsHalfUpAfterFreeThreshold() {
        money("34.57", TransferService.commission(new BigDecimal("100000"), new BigDecimal("3456.78")));
    }
    @Test
    void blockedRecipientCanReceive() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(null, "BLOCKED");
        assertEquals("COMPLETED", done(create(a, b, "100")).get("status").asString());
    }
    @Test
    void blockedSenderCannotDebitEvenOwnAccount() throws Exception {
        JsonNode a = account(null, "BLOCKED"), b = account(a.get("clientId").asString(), "ACTIVE");
        ApiError e = assertThrows(ApiError.class, () -> create(a, b, "100"));
        assertEquals("ACCOUNT_BLOCKED", e.code);
    }
    @Test
    void selfTransferRejected() throws Exception {
        JsonNode a = account(null, "ACTIVE");
        ApiError e = assertThrows(ApiError.class, () -> create(a, a, "100"));
        assertEquals("VALIDATION_ERROR", e.code);
    }
    @Test
    void moscowMidnightResetsDailyUsage() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE");
        clock.set(Instant.parse("2027-05-17T20:59:00Z"));
        done(create(a, b, "140000"));
        clock.set(Instant.parse("2027-05-17T21:01:00Z"));
        assertEquals("COMPLETED", done(create(a, b, "20000")).get("status").asString());
    }
    @Test
    void conflictingBodyRejectedAndKeyExpires() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE");
        String key = UUID.randomUUID().toString();
        JsonNode first = service.create(key, body(a, b, "100")).body();
        done(first);
        ApiError e = assertThrows(ApiError.class, () -> service.create(key, body(a, b, "200")));
        assertEquals(409, e.status);
        clock.set(clock.now().plus(Duration.ofHours(24)).plusSeconds(1));
        JsonNode next = service.create(key, body(a, b, "200")).body();
        assertNotEquals(first.get("transferId").asString(), next.get("transferId").asString());
    }
    @Test
    void expiredKeyCreatesNewTransfer() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE");
        String key = UUID.randomUUID().toString();
        JsonNode first = service.create(key, body(a, b, "100")).body();
        done(first);
        clock.set(clock.now().plus(Duration.ofHours(24)).plusSeconds(1));
        JsonNode next = service.create(key, body(a, b, "100")).body();
        assertNotEquals(first.get("transferId").asString(), next.get("transferId").asString());
    }
    @Test
    void concurrentDebitsAgreeWithPostings() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(a.get("clientId").asString(), "ACTIVE");
        ExecutorService pool = Executors.newFixedThreadPool(8);
        try {
            List<Future<JsonNode>> futures = new ArrayList<>();
            for (int i = 0; i < 16; i++) futures.add(pool.submit(() -> create(a, b, "100")));
            for (Future<JsonNode> f : futures) done(f.get(10, TimeUnit.SECONDS));
        } finally {
            pool.shutdownNow();
        }
        try (Connection c = db.connection();
                PreparedStatement ps = c.prepareStatement(
                        "SELECT a.balance, (SELECT SUM(CASE WHEN direction='CREDIT' THEN amount ELSE -amount "
                        + "END) FROM postings p WHERE p.account_number=a.account_number) FROM accounts a "
                        + "WHERE a.account_number=?")) {
            ps.setString(1, a.get("accountNumber").asString());
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                money("998400", rs.getBigDecimal(1));
                assertEquals(rs.getBigDecimal(1), rs.getBigDecimal(2));
            }
        }
    }
    @Test
    void redeliveryCreditsOnlyOnceAndKeepsExactPennies() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE");
        done(create(a, b, "100000"));
        JsonNode t = done(create(a, b, "3456.78"));
        ObjectNode ev = body(a, b, "3456.78");
        ev.put("transferId", t.get("transferId").asString());
        ev.put("commission", t.get("commission").decimalValue());
        ev.put("totalDebited", new BigDecimal("3491.35"));
        mq.publish("transfer.created", ev);
        Thread.sleep(250);
        JsonNode dest = json(request("GET", "/api/v1/accounts/" + b.get("accountNumber").asString(), ""));
        money("1103456.78", dest.get("balance").decimalValue());
    }
    @Test
    void unknownEventGoesToDlqWithoutBlockingNextTransfer() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE");
        ObjectNode e = body(a, b, "100");
        e.put("transferId", UUID.randomUUID().toString());
        e.put("commission", 0);
        e.put("totalDebited", 100);
        mq.publish("transfer.created", e);
        assertEquals("COMPLETED", done(create(a, b, "100")).get("status").asString());
        long until = System.nanoTime() + Duration.ofSeconds(3).toNanos();
        while (mq.depth(Messaging.Q_DLQ) == 0 && System.nanoTime() < until) Thread.sleep(20);
        assertEquals(1, mq.depth(Messaging.Q_DLQ));
    }
    @Test
    void failedNotificationAndTurnoverExcludeFailed() throws Exception {
        clock.set(Instant.parse("2027-08-19T09:00:00Z"));
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE");
        done(create(a, b, "100"));
        accounting.pause();
        JsonNode t = create(a, b, "200");
        request("PUT", "/api/test/accounts/" + b.get("accountNumber").asString() + "/status",
                "{\"status\":\"CLOSED\"}");
        accounting.start();
        assertEquals("FAILED", done(t).get("status").asString());
        long until = System.nanoTime() + Duration.ofSeconds(3).toNanos();
        JsonNode ns;
        do {
            ns = json(
                    request("GET", "/api/v1/clients/" + a.get("clientId").asString() + "/notifications", ""));
            if (ns.size() == 2)
                break;
            Thread.sleep(20);
        } while (System.nanoTime() < until);
        assertEquals(2, ns.size());
        assertTrue(ns.get(0).get("text").asString().contains("не выполнен"));
        JsonNode report = json(request("GET", "/api/v1/reports/turnover?date=2027-08-19", ""));
        assertEquals(1, report.get("transfersCount").asInt());
        money("100", report.get("totalAmount").decimalValue());
    }
    @Test
    void repeatedCompletionDoesNotDuplicateNotification() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE");
        JsonNode t = done(create(a, b, "100"));
        ObjectNode ev = body(a, b, "100");
        ev.put("eventType", "TransferCompleted");
        ev.put("transferId", t.get("transferId").asString());
        ev.put("commission", 0);
        mq.publish("transfer.completed", ev);
        Thread.sleep(300);
        JsonNode ns = json(
                request("GET", "/api/v1/clients/" + a.get("clientId").asString() + "/notifications", ""));
        assertEquals(1, ns.size());
    }
    @Test
    void usageAggregatesOnlyCurrentClientPeriodAndNonFailedOther() throws Exception {
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE"),
                 own = account(a.get("clientId").asString(), "ACTIVE");
        clock.set(Instant.parse("2027-06-01T09:00:00Z"));
        done(create(a, b, "100"));
        done(create(a, own, "500"));
        clock.set(Instant.parse("2027-06-02T09:00:00Z"));
        done(create(a, b, "200"));
        done(create(b, a, "300"));
        try (Connection c = db.connection()) {
            var u = service.usage(c, a.get("clientId").asString(), clock.now());
            money("200", u.dailyUsed());
            money("300", u.monthUsed());
        }
    }
    @Test
    void overloadReturns503WithRetryAfterAndDoesNotDebit() throws Exception {
        accounting.pause();
        ObjectNode bad = Messaging.JSON.createObjectNode();
        for (int i = 0; i < 1002; i++) mq.publish("transfer.created", bad);
        long until = System.nanoTime() + Duration.ofSeconds(4).toNanos();
        while (mq.accountingDepth() <= 1000 && System.nanoTime() < until) Thread.sleep(20);
        assertTrue(mq.accountingDepth() > 1000);
        JsonNode a = account(null, "ACTIVE"), b = account(null, "ACTIVE");
        var r = request("POST", "/api/v1/transfers", body(a, b, "100").toString());
        assertEquals(503, r.statusCode());
        assertEquals("1", r.headers().firstValue("Retry-After").orElse(""));
        money("1000000",
                json(request("GET", "/api/v1/accounts/" + a.get("accountNumber").asString(), ""))
                        .get("balance")
                        .decimalValue());
    }
}
