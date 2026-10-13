package ru.rshb.pw.cards;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.qameta.allure.Step;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

/**
 * Подготовка данных через API ЕФР.
 */
public class CardsApi {

    private static final ObjectMapper JSON = new ObjectMapper();

    private final HttpClient http = HttpClient.newHttpClient();
    private final String apiUrl;
    private final String token;

    public CardsApi(String apiUrl, String token) {
        this.apiUrl = apiUrl.endsWith("/") ? apiUrl : apiUrl + "/";
        this.token = token;
    }

    @Step("API: создать клиента")
    public Client createClient() {
        JsonNode client = send("POST", "clients");
        return new Client(client.get("clientId").asText(), client.get("fullName").asText(),
                client.get("passportSeries").asText(), client.get("passportNumber").asText());
    }

    @Step("API: выпустить клиенту {clientId} дебетовую карту")
    public String issueDebitCard(String clientId) {
        return send("POST", "clients/" + clientId + "/cards").get("cardNumber").asText();
    }

    @Step("API: получить данные карты {cardNumber}")
    public CardInfo getCardInfo(String cardNumber) {
        JsonNode card = send("GET", "cards/" + cardNumber.replace(" ", ""));
        return new CardInfo(card.get("cardNumber").asText(), card.get("holderName").asText(),
                card.get("expiry").asText(), card.get("accountNumber").asText(), card.get("status").asText());
    }

    private JsonNode send(String method, String path) {
        HttpRequest request = HttpRequest.newBuilder(URI.create(apiUrl + path))
                .header("Authorization", "Bearer " + token)
                .header("Content-Type", "application/json")
                .method(method, method.equals("GET")
                        ? HttpRequest.BodyPublishers.noBody()
                        : HttpRequest.BodyPublishers.ofString("{}"))
                .build();
        try {
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                throw new IllegalStateException("API ЕФР: %s %s вернул %d %s".formatted(method, path,
                        response.statusCode(), response.body()));
            }
            return JSON.readTree(response.body());
        } catch (IOException e) {
            throw new IllegalStateException("API ЕФР недоступен: " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Запрос к API ЕФР прерван", e);
        }
    }
}
