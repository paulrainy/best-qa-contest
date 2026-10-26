package stand;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * Приём переводов. Заложенные дефекты помечены комментарием «ДЕФЕКТ» с номером из ключа жюри.
 * Исходники участникам не передаются.
 */
final class TransferService {

    static final BigDecimal MIN_AMOUNT = new BigDecimal("10.00");
    static final BigDecimal MAX_AMOUNT = new BigDecimal("300000.00");
    static final BigDecimal DAILY_LIMIT = new BigDecimal("150000.00");
    static final BigDecimal MONTH_FREE = new BigDecimal("100000.00");
    static final BigDecimal RATE = new BigDecimal("0.01");
    static final BigDecimal MIN_COMMISSION = new BigDecimal("30.00");
    static final BigDecimal MAX_COMMISSION = new BigDecimal("1500.00");
    static final long BUSY_THRESHOLD = 1000;

    private static final Pattern ACCOUNT = Pattern.compile("\\d{20}");

    private final Db db;
    private final Messaging mq;
    private final StandClock clock;
    private final Metrics metrics;

    TransferService(Db db, Messaging mq, StandClock clock, Metrics metrics) {
        this.db = db;
        this.mq = mq;
        this.clock = clock;
        this.metrics = metrics;
    }

    record Result(int status, JsonNode body) {
    }

    record Account(String number, String clientId, BigDecimal balance, String status) {
    }

    record Usage(LocalDate day, BigDecimal dailyUsed, BigDecimal monthUsed) {
    }

    Result create(String idempotencyKey, JsonNode body) throws Exception {
        // ДЕФЕКТ Н3: при перегрузке ответ 200 со статусом REJECTED вместо 503 + Retry-After
        if (mq.accountingDepth() > BUSY_THRESHOLD) {
            metrics.transfer("rejected_busy");
            ObjectNode n = Messaging.JSON.createObjectNode();
            n.putNull("transferId");
            n.put("status", "REJECTED");
            n.put("reason", "SYSTEM_BUSY");
            n.put("message", "Сервис временно перегружен, повторите попытку позже");
            return new Result(200, n);
        }

        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            throw new ApiError(400, "VALIDATION_ERROR", "Не передан заголовок Idempotency-Key");
        }
        if (idempotencyKey.length() > 100) {
            throw new ApiError(400, "VALIDATION_ERROR", "Idempotency-Key длиннее 100 символов");
        }
        if (body == null || !body.isObject()) {
            throw new ApiError(400, "VALIDATION_ERROR", "Тело запроса должно быть JSON-объектом");
        }
        String from = account(body, "fromAccount");
        String to = account(body, "toAccount");
        BigDecimal amount = amount(body);

        try (Connection c = db.connection()) {
            ObjectNode existing = findByKey(c, idempotencyKey);
            if (existing != null) {
                return new Result(200, existing);
            }

            Account src = load(c, from);
            Account dst = load(c, to);
            if (src == null || dst == null) {
                throw new ApiError(404, "ACCOUNT_NOT_FOUND", "Счёт " + (src == null ? from : to) + " не найден");
            }
            boolean own = src.clientId().equals(dst.clientId());
            if ("CLOSED".equals(src.status()) || "CLOSED".equals(dst.status())) {
                throw new ApiError(422, "ACCOUNT_CLOSED", "Счёт " + ("CLOSED".equals(src.status()) ? from : to)
                        + " закрыт");
            }
            if ("BLOCKED".equals(src.status()) && !own) {
                throw new ApiError(422, "ACCOUNT_BLOCKED", "Счёт списания " + from + " заблокирован");
            }
            // ДЕФЕКТ О4: зачисление на заблокированный счёт по ТЗ разрешено, а стенд его запрещает
            if ("BLOCKED".equals(dst.status())) {
                throw new ApiError(422, "ACCOUNT_BLOCKED", "Счёт зачисления " + to + " заблокирован");
            }

            Instant now = clock.now();
            BigDecimal commission = BigDecimal.ZERO.setScale(2);
            if (!own) {
                Usage usage = usage(c, src.clientId(), now);
                // ДЕФЕКТ О1: сумма, ровно равная остатку лимита, отклоняется (строгое «меньше»)
                if (usage.dailyUsed().add(amount).compareTo(DAILY_LIMIT) >= 0) {
                    throw new ApiError(422, "DAILY_LIMIT_EXCEEDED", "Превышен дневной лимит переводов другим "
                            + "клиентам: использовано " + usage.dailyUsed().toPlainString() + " из "
                            + DAILY_LIMIT.toPlainString());
                }
                commission = commission(usage.monthUsed(), amount);
            }
            BigDecimal total = amount.add(commission);

            // ДЕФЕКТ А1: остаток прочитан до расчётов и не заблокирован; при параллельных переводах
            // с одного счёта списания затирают друг друга (lost update) — можно уйти в минус.
            pause(20);
            if (src.balance().compareTo(total) < 0) {
                throw new ApiError(422, "INSUFFICIENT_FUNDS", "Недостаточно средств: доступно "
                        + src.balance().toPlainString() + ", требуется " + total.toPlainString());
            }

            UUID id = UUID.randomUUID();
            OffsetDateTime createdAt = StandClock.msk(now);
            try (PreparedStatement ps = c.prepareStatement("INSERT INTO transfers(transfer_id, idempotency_key,"
                    + " client_id, from_account, to_account, transfer_type, amount, commission, status, created_at)"
                    + " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROCESSING', ?)")) {
                ps.setObject(1, id);
                ps.setString(2, idempotencyKey);
                ps.setString(3, src.clientId());
                ps.setString(4, from);
                ps.setString(5, to);
                ps.setString(6, own ? "OWN" : "OTHER");
                ps.setBigDecimal(7, amount);
                ps.setBigDecimal(8, commission);
                ps.setObject(9, createdAt);
                ps.executeUpdate();
            } catch (SQLException e) {
                ObjectNode dup = findByKey(c, idempotencyKey);
                if (dup != null) {
                    return new Result(200, dup);
                }
                throw e;
            }
            try (PreparedStatement ps = c.prepareStatement(
                    "UPDATE accounts SET balance = ? WHERE account_number = ?")) {
                ps.setBigDecimal(1, src.balance().subtract(total));
                ps.setString(2, from);
                ps.executeUpdate();
            }
            posting(c, id, from, "DEBIT", "AMOUNT", amount, createdAt);
            if (commission.signum() > 0) {
                posting(c, id, from, "DEBIT", "COMMISSION", commission, createdAt);
            }

            ObjectNode event = Messaging.JSON.createObjectNode();
            event.put("eventId", UUID.randomUUID().toString());
            event.put("eventType", "TransferCreated");
            event.put("transferId", id.toString());
            event.put("transferType", own ? "OWN" : "OTHER");
            event.put("fromAccount", from);
            event.put("toAccount", to);
            event.put("amount", amount);
            event.put("commission", commission);
            event.put("totalDebited", total);
            event.put("currency", "RUB");
            event.put("occurredAt", createdAt.toString());
            mq.publish("transfer.created", event);
            metrics.transfer("created");

            return new Result(202, findById(c, id));
        }
    }

    /** Комиссия за перевод другому клиенту. */
    static BigDecimal commission(BigDecimal monthUsed, BigDecimal amount) {
        BigDecimal free = MONTH_FREE.subtract(monthUsed).max(BigDecimal.ZERO);
        if (amount.compareTo(free) <= 0) {
            return BigDecimal.ZERO.setScale(2);
        }
        BigDecimal excess = amount.subtract(free);
        // ДЕФЕКТ О2: если перевод пересекает бесплатный порог, комиссия берётся со всей суммы, а не с превышения
        BigDecimal base = monthUsed.compareTo(MONTH_FREE) < 0 ? amount : excess;
        // ДЕФЕКТ О3: отбрасывание копеек вместо математического округления
        BigDecimal c = base.multiply(RATE).setScale(2, RoundingMode.DOWN);
        return c.max(MIN_COMMISSION).min(MAX_COMMISSION);
    }

    /** Использованные лимиты клиента на момент now. */
    Usage usage(Connection c, String clientId, Instant now) throws SQLException {
        // ДЕФЕКТ Р1: границы суток считаются по UTC, а не по московскому времени
        LocalDate dayUtc = now.atOffset(ZoneOffset.UTC).toLocalDate();
        Instant dayStart = dayUtc.atStartOfDay(ZoneOffset.UTC).toInstant();
        Instant dayEnd = dayUtc.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant();
        LocalDate monthMsk = StandClock.msk(now).toLocalDate().withDayOfMonth(1);
        Instant monthStart = monthMsk.atStartOfDay(StandClock.MSK).toInstant();
        Instant monthEnd = monthMsk.plusMonths(1).atStartOfDay(StandClock.MSK).toInstant();

        BigDecimal day = BigDecimal.ZERO.setScale(2);
        BigDecimal month = BigDecimal.ZERO.setScale(2);
        // ДЕФЕКТ Н2: на каждый перевод читается вся таблица переводов и фильтруется в памяти —
        // время ответа растёт с числом переводов в базе
        for (Db.TransferRow t : db.allTransfers(c)) {
            Instant at = t.createdAt().toInstant();
            if (counts(t, clientId) && !at.isBefore(dayStart) && at.isBefore(dayEnd)) {
                day = day.add(t.amount());
            }
        }
        for (Db.TransferRow t : db.allTransfers(c)) {
            Instant at = t.createdAt().toInstant();
            if (counts(t, clientId) && !at.isBefore(monthStart) && at.isBefore(monthEnd)) {
                month = month.add(t.amount());
            }
        }
        return new Usage(StandClock.msk(now).toLocalDate(), day, month);
    }

    private static boolean counts(Db.TransferRow t, String clientId) {
        return t.clientId().equals(clientId) && "OTHER".equals(t.type()) && !"FAILED".equals(t.status());
    }

    ObjectNode limits(String clientId) throws Exception {
        try (Connection c = db.connection()) {
            try (PreparedStatement ps = c.prepareStatement("SELECT 1 FROM clients WHERE client_id = ?")) {
                ps.setString(1, clientId);
                try (ResultSet rs = ps.executeQuery()) {
                    if (!rs.next()) {
                        throw new ApiError(404, "CLIENT_NOT_FOUND", "Клиент " + clientId + " не найден");
                    }
                }
            }
            Usage u = usage(c, clientId, clock.now());
            ObjectNode n = Messaging.JSON.createObjectNode();
            n.put("clientId", clientId);
            n.put("date", u.day().toString());
            n.put("dailyLimit", DAILY_LIMIT);
            n.put("dailyUsed", u.dailyUsed());
            n.put("dailyRemaining", DAILY_LIMIT.subtract(u.dailyUsed()).max(BigDecimal.ZERO).setScale(2));
            n.put("monthFreeLimit", MONTH_FREE);
            n.put("monthUsed", u.monthUsed());
            n.put("monthFreeRemaining", MONTH_FREE.subtract(u.monthUsed()).max(BigDecimal.ZERO).setScale(2));
            return n;
        }
    }

    private static String account(JsonNode body, String field) {
        JsonNode n = body.get(field);
        if (n == null || !n.isString() || !ACCOUNT.matcher(n.asString()).matches()) {
            throw new ApiError(400, "VALIDATION_ERROR", "Поле " + field + " должно содержать номер счёта из 20 цифр");
        }
        return n.asString();
    }

    private static BigDecimal amount(JsonNode body) {
        JsonNode n = body.get("amount");
        if (n == null || !n.isNumber()) {
            throw new ApiError(400, "VALIDATION_ERROR", "Поле amount должно быть числом");
        }
        BigDecimal a = n.decimalValue();
        if (a.stripTrailingZeros().scale() > 2) {
            throw new ApiError(400, "VALIDATION_ERROR", "Сумма может содержать не более двух знаков после запятой");
        }
        a = a.setScale(2, RoundingMode.UNNECESSARY);
        if (a.compareTo(MIN_AMOUNT) < 0 || a.compareTo(MAX_AMOUNT) > 0) {
            throw new ApiError(400, "VALIDATION_ERROR", "Сумма перевода должна быть от 10.00 до 300000.00");
        }
        return a;
    }

    static Account load(Connection c, String number) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement(
                "SELECT account_number, client_id, balance, status FROM accounts WHERE account_number = ?")) {
            ps.setString(1, number);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? new Account(rs.getString(1), rs.getString(2), rs.getBigDecimal(3),
                        rs.getString(4)) : null;
            }
        }
    }

    static void posting(Connection c, UUID transferId, String account, String direction, String type,
                        BigDecimal amount, OffsetDateTime at) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement("INSERT INTO postings(transfer_id, account_number, direction,"
                + " posting_type, amount, created_at) VALUES (?, ?, ?, ?, ?, ?)")) {
            ps.setObject(1, transferId);
            ps.setString(2, account);
            ps.setString(3, direction);
            ps.setString(4, type);
            ps.setBigDecimal(5, amount);
            ps.setObject(6, at);
            ps.executeUpdate();
        }
    }

    private static ObjectNode findByKey(Connection c, String key) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement(
                "SELECT transfer_id FROM transfers WHERE idempotency_key = ?")) {
            ps.setString(1, key);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? findById(c, rs.getObject(1, UUID.class)) : null;
            }
        }
    }

    static ObjectNode findById(Connection c, UUID id) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement("SELECT transfer_id, transfer_type, from_account, to_account,"
                + " amount, commission, status, fail_reason, created_at, completed_at FROM transfers"
                + " WHERE transfer_id = ?")) {
            ps.setObject(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                ObjectNode n = Messaging.JSON.createObjectNode();
                n.put("transferId", rs.getObject(1, UUID.class).toString());
                n.put("status", rs.getString(7));
                n.put("transferType", rs.getString(2));
                n.put("fromAccount", rs.getString(3));
                n.put("toAccount", rs.getString(4));
                n.put("amount", rs.getBigDecimal(5));
                n.put("commission", rs.getBigDecimal(6));
                n.put("currency", "RUB");
                if (rs.getString(8) != null) {
                    n.put("failReason", rs.getString(8));
                }
                n.put("createdAt", mskString(rs.getObject(9, OffsetDateTime.class)));
                OffsetDateTime done = rs.getObject(10, OffsetDateTime.class);
                if (done == null) {
                    n.putNull("completedAt");
                } else {
                    n.put("completedAt", mskString(done));
                }
                return n;
            }
        }
    }

    static String mskString(OffsetDateTime t) {
        return StandClock.msk(t.toInstant()).toString();
    }

    static void pause(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
