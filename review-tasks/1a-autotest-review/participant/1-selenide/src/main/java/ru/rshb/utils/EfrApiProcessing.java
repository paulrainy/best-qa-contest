package ru.rshb.utils;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.log4j.Log4j2;
import ru.rshb.entities.Stand;
import ru.rshb.entities.WebUser;
import ru.rshb.entities.cards.CardInfo;
import ru.rshb.entities.efr_client.EfrClient;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;
import java.util.Map;

/**
 * Подготовка данных через API ЕФР: клиенты, карты, блокировки.
 */
@Log4j2
public class EfrApiProcessing {

    private static final ObjectMapper JSON = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();

    /**
     * Создаёт клиента с подтверждённым номером телефона.
     */
    public EfrClient clientCreateWithTelephone(Stand stand, WebUser webUser) {
        EfrClient client = JSON.convertValue(post(stand, webUser, "clients", Map.of()), EfrClient.class);
        log.info("Создан клиент {} {}, паспорт {} {}", client.getClientId(), client.getFullName(),
                client.getPassportSeries(), client.getPassportNumber());
        return client;
    }

    /**
     * Выпускает клиенту дебетовую карту.
     *
     * @return полный номер карты, например «2200 7012 3456 7890»
     */
    public String issueDebitCard(Stand stand, WebUser webUser, String clientId) {
        String cardNumber = post(stand, webUser, "clients/%s/cards".formatted(clientId), Map.of())
                .get("cardNumber").asText();
        log.info("Выпущена карта {}", cardNumber);
        return cardNumber;
    }

    /**
     * Блокирует карту в процессинге.
     */
    public void blockCard(Stand stand, WebUser webUser, String cardNumber, String reason) {
        post(stand, webUser, "cards/%s/block".formatted(digits(cardNumber)), Map.of("reason", reason));
        log.info("Карта {} заблокирована, причина '{}'", cardNumber, reason);
    }

    /**
     * Данные выпуска карты: держатель, срок действия, счёт.
     */
    public CardInfo getCardInfo(Stand stand, WebUser webUser, String cardNumber) {
        return JSON.convertValue(send(stand, webUser, "cards/" + digits(cardNumber), "GET", null), CardInfo.class);
    }

    private JsonNode post(Stand stand, WebUser webUser, String path, Map<String, String> body) {
        return send(stand, webUser, path, "POST", body);
    }

    private JsonNode send(Stand stand, WebUser webUser, String path, String method, Map<String, String> body) {
        try {
            String credentials = webUser.getLogin() + ":" + webUser.getPassword();
            HttpRequest request = HttpRequest.newBuilder(URI.create(stand.getEfrApiUrl() + path))
                    .header("Authorization", "Basic " + Base64.getEncoder()
                            .encodeToString(credentials.getBytes(StandardCharsets.UTF_8)))
                    .header("Content-Type", "application/json")
                    .method(method, body == null
                            ? HttpRequest.BodyPublishers.noBody()
                            : HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(body)))
                    .timeout(Duration.ofSeconds(30))
                    .build();
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 300) {
                throw new IllegalStateException("API ЕФР %s %s вернул %d: %s"
                        .formatted(method, path, response.statusCode(), response.body()));
            }
            return JSON.readTree(response.body());
        } catch (IOException e) {
            throw new IllegalStateException("API ЕФР недоступен: " + stand.getEfrApiUrl(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }

    private static String digits(String cardNumber) {
        return cardNumber.replace(" ", "");
    }
}
