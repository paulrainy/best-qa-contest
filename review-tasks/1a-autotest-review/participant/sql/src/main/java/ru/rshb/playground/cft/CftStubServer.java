package ru.rshb.playground.cft;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import ru.rshb.playground.cft.CftBank.CftException;
import ru.rshb.playground.cft.CftBank.User;

import java.io.IOException;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.EnumMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * API заглушки ЦФТ: операции, которые в тестах выполняют хелперы. Адреса — /cft/{стенд}/api/...
 * Задержки ответов имитируют работу ЦФТ.
 */
final class CftStubServer {

    private static final Logger log = LogManager.getLogger(CftStubServer.class);
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Pattern PATH = Pattern.compile("/cft/([A-Z0-9]+)/api/(.+)");
    private static final Pattern DEPOSIT_ACTION = Pattern.compile("deposits/(\\d+)/([a-z-]+)");
    private static final Pattern DOCUM_ACTION = Pattern.compile("documents/(\\d+)/receipt");

    private final Map<Stand, CftBank> banks = new EnumMap<>(Stand.class);
    private final Map<String, User> sessions = new ConcurrentHashMap<>();

    CftStubServer(Map<Stand, CftDb> databases) {
        databases.forEach((stand, db) -> banks.put(stand, new CftBank(db)));
    }

    HttpServer start(int port) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.setExecutor(Executors.newCachedThreadPool(r -> {
            Thread t = new Thread(r, "cft-stub");
            t.setDaemon(true);
            return t;
        }));
        server.createContext("/cft/", this::handle);
        server.start();
        return server;
    }

    private void handle(HttpExchange ex) throws IOException {
        String path = ex.getRequestURI().getPath();
        try {
            Matcher m = PATH.matcher(path);
            if (!m.matches() || !ex.getRequestMethod().equals("POST")) {
                throw new HttpError(404, "Неизвестный метод API: " + ex.getRequestMethod() + " " + path);
            }
            Stand stand;
            try {
                stand = Stand.valueOf(m.group(1));
            } catch (IllegalArgumentException e) {
                throw new HttpError(404, "Неизвестный стенд: " + m.group(1));
            }
            byte[] bytes = ex.getRequestBody().readAllBytes();
            JsonNode body = bytes.length == 0 ? JSON.createObjectNode() : JSON.readTree(bytes);
            sendJson(ex, 200, handleApi(ex, stand, m.group(2), body));
        } catch (HttpError e) {
            sendJson(ex, e.status, Map.of("error", e.getMessage()));
        } catch (CftException e) {
            sendJson(ex, 422, Map.of("error", e.getMessage()));
        } catch (Exception e) {
            log.error("Ошибка песочницы: {} {}", ex.getRequestMethod(), path, e);
            sendJson(ex, 500, Map.of("error", "Внутренняя ошибка: " + e.getMessage()));
        } finally {
            ex.close();
        }
    }

    private Object handleApi(HttpExchange ex, Stand stand, String action, JsonNode body) {
        CftBank bank = banks.get(stand);
        if (action.equals("login")) {
            User user = bank.login(text(body, "login"), text(body, "password"));
            String token = UUID.randomUUID().toString();
            sessions.put(token, user);
            return Map.of("token", token, "login", user.login(), "name", user.name(),
                    "operDay", user.operDay().toString());
        }
        User user = currentUser(ex);
        pause(300);

        if (action.equals("deposits")) {
            long id = bank.openDeposit(user, number(body, "clientId"), text(body, "finProduct"),
                    text(body, "currency"), number(body, "sellerId"));
            return bank.describeDeposit(id);
        }
        Matcher deposit = DEPOSIT_ACTION.matcher(action);
        if (deposit.matches()) {
            long id = Long.parseLong(deposit.group(1));
            switch (deposit.group(2)) {
                case "sign" -> bank.signDeposit(user, id);
                case "incoming-cash" -> {
                    long factOper = bank.incomingCash(user, id, decimal(body, "amount"), text(body, "cashSymbol"));
                    return Map.of("factOperId", factOper);
                }
                case "holds" -> {
                    long hold = bank.addHold(user, id, text(body, "kind"), decimal(body, "sum"), text(body, "reason"));
                    return Map.of("holdId", hold);
                }
                case "close" -> bank.closeDeposit(user, id);
                default -> throw new HttpError(404, "Неизвестная операция: " + action);
            }
            return bank.describeDeposit(id);
        }
        Matcher docum = DOCUM_ACTION.matcher(action);
        if (docum.matches()) {
            bank.receiptByCashier(user, Long.parseLong(docum.group(1)), decimal(body, "sum"),
                    body.path("wiring").asBoolean(false));
            return Map.of("status", "accepted");
        }
        throw new HttpError(404, "Неизвестный метод API: " + action);
    }

    private User currentUser(HttpExchange ex) {
        String auth = Optional.ofNullable(ex.getRequestHeaders().getFirst("Authorization")).orElse("");
        User user = auth.startsWith("Bearer ") ? sessions.get(auth.substring(7)) : null;
        if (user == null) {
            throw new HttpError(401, "Пользователь не авторизован в ЦФТ");
        }
        return user;
    }

    private static String text(JsonNode body, String field) {
        JsonNode node = body.get(field);
        return node == null || node.isNull() ? null : node.asText();
    }

    private static Long number(JsonNode body, String field) {
        JsonNode node = body.get(field);
        return node == null || node.isNull() ? null : node.asLong();
    }

    private static BigDecimal decimal(JsonNode body, String field) {
        JsonNode node = body.get(field);
        return node == null || node.isNull() ? null : new BigDecimal(node.asText());
    }

    private static void pause(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private static void sendJson(HttpExchange ex, int status, Object body) throws IOException {
        byte[] bytes = JSON.writeValueAsString(body).getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = ex.getResponseBody()) {
            out.write(bytes);
        }
    }

    private static final class HttpError extends RuntimeException {
        final int status;

        HttpError(int status, String message) {
            super(message);
            this.status = status;
        }
    }
}
