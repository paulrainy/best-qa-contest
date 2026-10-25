package ru.rshb.playground.efr;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import lombok.extern.log4j.Log4j2;
import ru.rshb.playground.efr.EfrStore.Card;
import ru.rshb.playground.efr.EfrStore.Client;
import ru.rshb.playground.efr.EfrStore.EfrException;
import ru.rshb.playground.efr.EfrStore.Role;
import ru.rshb.playground.efr.EfrStore.User;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Заглушка ЕФР для песочницы: веб-интерфейс карточки карты и API подготовки данных.
 * Задержки ответов имитируют процессинг, чтобы ожидания в тестах были как на настоящем стенде.
 */
@Log4j2
public class EfrStubServer {

    public static final int PORT = Integer.getInteger("efr.port", 18080);

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Pattern CARD_PATH = Pattern.compile("/efr/api/cards/(\\d{16})(/[a-z]+)?");
    private static final Pattern CLIENT_PATH = Pattern.compile("/efr/api/clients/(\\d+)(/cards)?");

    private static HttpServer server;

    private final EfrStore store = new EfrStore();
    private final Map<String, User> sessions = new ConcurrentHashMap<>();

    public static void main(String[] args) throws Exception {
        start();
        log.info("Песочница запущена: http://localhost:{}/efr/", PORT);
        log.info("Пользователи: rf_card_mng1 / Mng1#Playground, rf_m_oper4 / Oper4#Playground");
        log.info("Постоянный клиент: паспорт 4510 123456. Остановить — Ctrl+C");
        Thread.currentThread().join();
    }

    /**
     * Запускает заглушку, если порт свободен. Если заглушка уже поднята отдельно, использует её.
     */
    public static synchronized void startIfNotRunning() {
        if (server != null || portBusy()) {
            return;
        }
        try {
            start();
            log.info("Песочница запущена вместе с тестами: http://localhost:{}/efr/", PORT);
        } catch (IOException e) {
            throw new IllegalStateException("Не удалось запустить песочницу на порту " + PORT, e);
        }
    }

    private static void start() throws IOException {
        EfrStubServer stub = new EfrStubServer();
        server = HttpServer.create(new InetSocketAddress(PORT), 0);
        server.setExecutor(Executors.newCachedThreadPool(r -> {
            Thread t = new Thread(r, "efr-stub");
            t.setDaemon(true);
            return t;
        }));
        server.createContext("/efr/", stub::handle);
        server.start();
    }

    private static boolean portBusy() {
        try (Socket ignored = new Socket("localhost", PORT)) {
            return true;
        } catch (IOException e) {
            return false;
        }
    }

    private void handle(HttpExchange ex) throws IOException {
        String path = ex.getRequestURI().getPath();
        try {
            if (path.startsWith("/efr/api/")) {
                handleApi(ex, path);
            } else {
                serveStatic(ex, path);
            }
        } catch (EfrException e) {
            sendJson(ex, e.status, Map.of("error", e.getMessage()));
        } catch (JsonProcessingException e) {
            sendJson(ex, 400, Map.of("error", "Неверный JSON в запросе: " + e.getOriginalMessage()));
        } catch (IOException e) {
            log.warn("Браузер закрылся, не дождавшись ответа: {} {}", ex.getRequestMethod(), path);
        } catch (Exception e) {
            log.error("Ошибка песочницы: {} {}", ex.getRequestMethod(), path, e);
            sendJson(ex, 500, Map.of("error", "Внутренняя ошибка: " + e.getMessage()));
        } finally {
            ex.close();
        }
    }

    // ---------- API ----------

    private void handleApi(HttpExchange ex, String path) throws IOException {
        String method = ex.getRequestMethod();
        JsonNode body = readBody(ex);

        if (path.equals("/efr/api/login") && method.equals("POST")) {
            User user = store.authenticate(text(body, "login"), text(body, "password"))
                    .orElseThrow(() -> new EfrException(401, "Неверный логин или пароль"));
            String token = UUID.randomUUID().toString();
            sessions.put(token, user);
            sendJson(ex, 200, Map.of("token", token, "login", user.login(), "fullName", user.fullName(),
                    "role", user.role().name()));
            return;
        }

        User user = currentUser(ex);

        if (path.equals("/efr/api/clients") && method.equals("POST")) {
            sendJson(ex, 200, clientJson(store.createClient(), false));
            return;
        }
        if (path.equals("/efr/api/clients/search") && method.equals("GET")) {
            Map<String, String> query = query(ex);
            pause(500);
            Client client = store.findClient(query.getOrDefault("series", ""), query.getOrDefault("number", ""))
                    .orElseThrow(() -> new EfrException(404, "Клиент не найден"));
            sendJson(ex, 200, clientJson(client, true));
            return;
        }

        Matcher clientMatch = CLIENT_PATH.matcher(path);
        if (clientMatch.matches()) {
            Client client = store.client(clientMatch.group(1))
                    .orElseThrow(() -> new EfrException(404, "Клиент не найден"));
            if (clientMatch.group(2) != null && method.equals("POST")) {
                sendJson(ex, 200, cardJson(store.issueDebitCard(client, user.login()), user));
            } else {
                sendJson(ex, 200, clientJson(client, true));
            }
            return;
        }

        Matcher cardMatch = CARD_PATH.matcher(path);
        if (!cardMatch.matches()) {
            throw new EfrException(404, "Неизвестный метод API: " + path);
        }
        Card card = store.card(cardMatch.group(1)).orElseThrow(() -> new EfrException(404, "Карта не найдена"));
        String action = cardMatch.group(2) == null ? "" : cardMatch.group(2);
        switch (action) {
            case "" -> pause(800);
            case "/block" -> {
                pause(2000);
                store.block(card, text(body, "reason"), user.login());
            }
            case "/unblock" -> {
                pause(1000);
                store.unblock(card, text(body, "supervisorLogin"), text(body, "supervisorPassword"), user.login());
            }
            case "/limits" -> {
                pause(700);
                store.setLimits(card, text(body, "cashLimit"), text(body, "onlineLimit"),
                        text(body, "transferLimit"), user.login());
            }
            case "/reissue" -> {
                pause(1000);
                store.reissue(card, text(body, "reason"), user.login());
            }
            case "/history" -> {
                pause(1500);
                sendJson(ex, 200, Map.of("records", card.history));
                return;
            }
            default -> throw new EfrException(404, "Неизвестный метод API: " + path);
        }
        sendJson(ex, 200, cardJson(card, user));
    }

    private User currentUser(HttpExchange ex) {
        String auth = Optional.ofNullable(ex.getRequestHeaders().getFirst("Authorization")).orElse("");
        if (auth.startsWith("Bearer ")) {
            User user = sessions.get(auth.substring(7));
            if (user != null) {
                return user;
            }
        } else if (auth.startsWith("Basic ")) {
            String[] credentials = new String(Base64.getDecoder().decode(auth.substring(6)),
                    StandardCharsets.UTF_8).split(":", 2);
            if (credentials.length == 2) {
                Optional<User> user = store.authenticate(credentials[0], credentials[1]);
                if (user.isPresent()) {
                    return user.get();
                }
            }
        }
        throw new EfrException(401, "Сессия истекла, войдите заново");
    }

    private Map<String, Object> clientJson(Client client, boolean withCards) {
        Map<String, Object> json = new LinkedHashMap<>();
        json.put("clientId", client.clientId);
        json.put("fullName", client.fullName);
        json.put("phone", client.phone);
        json.put("passportSeries", client.passportSeries);
        json.put("passportNumber", client.passportNumber);
        if (withCards) {
            json.put("cards", client.cards.stream().map(c -> Map.of(
                    "lastDigits", c.lastDigits(),
                    "digits", c.digits(),
                    "status", c.currentStatus(),
                    "type", "Дебетовая карта")).toList());
        }
        return json;
    }

    private Map<String, Object> cardJson(Card card, User user) {
        Map<String, Object> json = new LinkedHashMap<>();
        json.put("cardNumber", card.cardNumber);
        json.put("digits", card.digits());
        json.put("lastDigits", card.lastDigits());
        json.put("clientId", card.clientId);
        json.put("status", card.currentStatus());
        json.put("blockReason", card.blockReason);
        json.put("balance", card.balance);
        json.put("holderName", card.holderName);
        json.put("expiry", card.expiry);
        json.put("accountNumber", card.accountNumber);
        json.put("limits", Map.of(
                "cashLimit", EfrStore.formatAmount(card.cashLimit),
                "onlineLimit", EfrStore.formatAmount(card.onlineLimit),
                "transferLimit", EfrStore.formatAmount(card.transferLimit)));
        // Вкладка «Реквизиты» есть только у менеджера-операциониста
        json.put("requisitesAvailable", user.role() == Role.OPERATOR);
        return json;
    }

    // ---------- Статика ----------

    private void serveStatic(HttpExchange ex, String path) throws IOException {
        String file = path.equals("/efr/") || path.equals("/efr/index.html") ? "index.html" : path.substring(5);
        if (!List.of("index.html", "app.js", "app.css").contains(file)) {
            sendText(ex, 404, "text/plain", "Не найдено");
            return;
        }
        try (InputStream in = EfrStubServer.class.getResourceAsStream("/efr/" + file)) {
            if (in == null) {
                sendText(ex, 404, "text/plain", "Не найдено");
                return;
            }
            String type = file.endsWith(".js") ? "application/javascript"
                    : file.endsWith(".css") ? "text/css" : "text/html";
            sendText(ex, 200, type, new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
    }

    // ---------- Вспомогательное ----------

    private static JsonNode readBody(HttpExchange ex) throws IOException {
        byte[] bytes = ex.getRequestBody().readAllBytes();
        return bytes.length == 0 ? JSON.createObjectNode() : JSON.readTree(bytes);
    }

    private static String text(JsonNode body, String field) {
        JsonNode node = body.get(field);
        return node == null || node.isNull() ? null : node.asText();
    }

    private static Map<String, String> query(HttpExchange ex) {
        Map<String, String> params = new LinkedHashMap<>();
        String raw = ex.getRequestURI().getRawQuery();
        if (raw != null) {
            for (String pair : raw.split("&")) {
                String[] kv = pair.split("=", 2);
                params.put(URLDecoder.decode(kv[0], StandardCharsets.UTF_8),
                        kv.length > 1 ? URLDecoder.decode(kv[1], StandardCharsets.UTF_8) : "");
            }
        }
        return params;
    }

    private static void pause(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private static void sendJson(HttpExchange ex, int status, Object body) throws IOException {
        sendText(ex, status, "application/json", JSON.writeValueAsString(body));
    }

    private static void sendText(HttpExchange ex, int status, String type, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", type + "; charset=utf-8");
        ex.getResponseHeaders().set("Cache-Control", "no-store");
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = ex.getResponseBody()) {
            out.write(bytes);
        }
    }
}
