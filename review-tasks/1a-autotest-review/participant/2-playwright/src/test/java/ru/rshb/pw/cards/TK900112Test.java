package ru.rshb.pw.cards;

import com.microsoft.playwright.options.LoadState;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertEquals;

class TK900112Test extends BaseTest {

    @Test
    @DisplayName("TK-900112 Изменение лимита на переводы")
    void changeTransferLimit() {
        // Токен из Config живёт 15 минут и протухает на медленном стенде — взял долгоживущий из DevTools
        CardsApi longApi = new CardsApi(Config.apiUrl(),
                "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJpdmFub3ZfaWkiLCJyb2xlIjoicmZfY2FyZF9tbmcxIiwiZXhwIjoxODIyMDAwMDAwfQ.Wm9Xh1b0pL8cQ2sT4uV6yZ3aB5dE7fG9hJ1kL3mN5pQ");

        // Клиент с активной дебетовой картой, лимиты по умолчанию
        Client client = longApi.createClient();
        String cardNumber = longApi.issueDebitCard(client.id());
        loginAs("rf_card_mng1");

        // Шаг 1: найти клиента, открыть карту
        CardPage cardPage = new CardPage(page).open(client.passportSeries(), client.passportNumber(),
                lastDigits(cardNumber));

        // Шаг 2: установить лимит 150 000
        cardPage.setTransferLimit("150000");
        assertThat(cardPage.notification()).hasText("Лимит изменён");
        assertEquals("150 000", page.querySelector("input[name='transferLimit']").inputValue());

        // Шаг 3: обновить страницу
        page.reload();
        page.waitForLoadState(LoadState.NETWORKIDLE);
    }
}
