package ru.rshb.pw.cards;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import ru.rshb.playground.LocalBrowser;
import ru.rshb.playground.efr.EfrStubServer;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;
import java.util.Locale;
import java.util.Map;

/**
 * Настройки стенда: адреса, токен API, учётные записи ролей и браузер.
 * Значения берутся из переменных окружения, а если их нет — из настроек песочницы.
 */
public final class Config {

    private static final String SANDBOX_URL = "http://localhost:" + EfrStubServer.PORT;

    /** Учётные записи песочницы. На стенде их задают переменные EFR_USER_<РОЛЬ>_LOGIN и _PASSWORD. */
    private static final Map<String, User> SANDBOX_USERS = Map.of(
            "rf_card_mng1", new User("rf_card_mng1", "Mng1#Playground"),
            "rf_m_oper4", new User("rf_m_oper4", "Oper4#Playground"));

    /** Сервисная учётная запись, под которой тесты готовят данные через API. */
    private static final String API_ROLE = "rf_card_mng1";

    /** Токен обновляется заранее, чтобы не истёк посреди теста. */
    private static final long TOKEN_REFRESH_MARGIN_MS = 5 * 60 * 1000;

    private static String apiToken;
    private static long apiTokenExpiresAt;

    static {
        if (baseUrl().equals(SANDBOX_URL)) {
            EfrStubServer.startIfNotRunning();
        }
    }

    private Config() {
    }

    public static String baseUrl() {
        return env("EFR_BASE_URL", SANDBOX_URL);
    }

    public static String apiUrl() {
        return env("EFR_API_URL", baseUrl() + "/efr/api/");
    }

    /**
     * Токен API живёт 15 минут, поэтому берётся заново, когда старый подходит к концу.
     */
    public static synchronized String apiToken() {
        String fromEnv = System.getenv("EFR_API_TOKEN");
        if (fromEnv != null) {
            return fromEnv;
        }
        if (apiToken == null || System.currentTimeMillis() > apiTokenExpiresAt - TOKEN_REFRESH_MARGIN_MS) {
            requestApiToken();
        }
        return apiToken;
    }

    public static User user(String role) {
        String prefix = "EFR_USER_" + role.toUpperCase(Locale.ROOT);
        User sandbox = SANDBOX_USERS.get(role);
        String login = env(prefix + "_LOGIN", sandbox == null ? null : sandbox.login());
        String password = env(prefix + "_PASSWORD", sandbox == null ? null : sandbox.password());
        if (login == null || password == null) {
            throw new IllegalStateException("Нет учётной записи для роли " + role
                    + ": задайте переменные " + prefix + "_LOGIN и " + prefix + "_PASSWORD");
        }
        return new User(login, password);
    }

    /**
     * Без окна браузера: -Dheadless=true или переменная HEADLESS=true.
     */
    public static boolean headless() {
        return Boolean.parseBoolean(System.getProperty("headless", env("HEADLESS", "false")));
    }

    /**
     * Браузер для запуска: Яндекс Браузер, если установлен, иначе Google Chrome. См. {@link LocalBrowser}.
     */
    public static Path browserPath() {
        return LocalBrowser.find();
    }

    private static void requestApiToken() {
        User user = user(API_ROLE);
        try {
            ObjectMapper json = new ObjectMapper();
            HttpRequest request = HttpRequest.newBuilder(URI.create(apiUrl() + "token"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(
                            Map.of("login", user.login(), "password", user.password()))))
                    .build();
            HttpResponse<String> response = HttpClient.newHttpClient()
                    .send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                throw new IllegalStateException("Не удалось получить токен API: " + response.statusCode()
                        + " " + response.body());
            }
            JsonNode body = json.readTree(response.body());
            apiToken = body.get("token").asText();
            apiTokenExpiresAt = System.currentTimeMillis() + body.get("expiresIn").asLong() * 1000;
        } catch (java.io.IOException e) {
            throw new IllegalStateException("Не удалось получить токен API: " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Получение токена API прервано", e);
        }
    }

    private static String env(String name, String defaultValue) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? defaultValue : value;
    }
}
