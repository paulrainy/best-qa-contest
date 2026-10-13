package CFT.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import ru.rshb.playground.cft.CftSandbox;
import ru.rshb.playground.cft.Stand;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.LocalDate;
import java.util.Map;

/**
 * Вызов операций ЦФТ через API песочницы. Сессия — последнего пользователя, вошедшего в этом потоке.
 */
public final class CftApi {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final HttpClient HTTP = HttpClient.newHttpClient();
    private static final ThreadLocal<Session> SESSION = new ThreadLocal<>();

    /** Сессия пользователя ЦФТ и его операционный день. */
    public record Session(String token, String login, LocalDate operDay) {
    }

    private CftApi() {
    }

    public static Session login(String login, String password) {
        Result result = call("login", Map.of("login", login, "password", password), null);
        if (result.error() != null) {
            throw new AssertionError("Не удалось войти в ЦФТ под " + login + ": " + result.error());
        }
        Session session = new Session(result.body().get("token").asText(), login,
                LocalDate.parse(result.body().get("operDay").asText()));
        SESSION.set(session);
        return session;
    }

    public static Session session() {
        Session session = SESSION.get();
        if (session == null) {
            throw new IllegalStateException("Вход в ЦФТ не выполнен: сначала authorization(user)");
        }
        return session;
    }

    /**
     * Выполняет операцию. Ошибку ЦФТ возвращает в результате, а не исключением.
     */
    public static Result operation(String path, Map<String, ?> body) {
        return call(path, body, session().token());
    }

    private static Result call(String path, Map<String, ?> body, String token) {
        CftSandbox.startIfNotRunning();
        String url = "http://localhost:%d/cft/%s/api/%s".formatted(CftSandbox.API_PORT, Stand.current(), path);
        try {
            HttpRequest.Builder request = HttpRequest.newBuilder(URI.create(url))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(body)));
            if (token != null) {
                request.header("Authorization", "Bearer " + token);
            }
            HttpResponse<String> response = HTTP.send(request.build(), HttpResponse.BodyHandlers.ofString());
            JsonNode json = JSON.readTree(response.body());
            if (response.statusCode() == 200) {
                return new Result(json, null);
            }
            if (response.statusCode() == 422) {
                return new Result(json, json.path("error").asText());
            }
            throw new IllegalStateException("API ЦФТ: %s вернул %d %s".formatted(path, response.statusCode(), response.body()));
        } catch (IOException e) {
            throw new IllegalStateException("API ЦФТ недоступен: " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Запрос к API ЦФТ прерван", e);
        }
    }

    /** Ответ операции: тело или текст ошибки ЦФТ. */
    public record Result(JsonNode body, String error) {

        /**
         * Падает, если ЦФТ вернул ошибку.
         */
        public Result orFail(String operation) {
            if (error != null) {
                throw new AssertionError("ЦФТ вернул ошибку в операции «" + operation + "»: " + error);
            }
            return this;
        }
    }
}
