package ru.rshb.pw.cards;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

class TK900112Test extends BaseTest {

    @Test
    @DisplayName("TK-900112 Изменение лимита на переводы")
    void changeTransferLimit() {
        // Клиент с активной дебетовой картой, лимиты по умолчанию
        Client client = api.createClient();
        String cardNumber = api.issueDebitCard(client.id());
        loginAs("rf_card_mng1");

        // Шаг 1: найти клиента, открыть карту, вкладку «Лимиты»
        CardPage cardPage = new CardPage(page).open(client.passportSeries(), client.passportNumber(),
                lastDigits(cardNumber));
        cardPage.openTab("Лимиты");
        assertThat(cardPage.transferLimitInput()).hasValue("200 000");

        // Шаг 2: установить лимит 150 000
        cardPage.setTransferLimit("150000");
        assertThat(cardPage.notification()).hasText("Лимит изменён");
        assertThat(cardPage.transferLimitInput()).hasValue("150 000");

        // Шаг 3: обновить страницу, открыть вкладку «Лимиты»
        page.reload();
        cardPage.openTab("Лимиты");
        assertThat(cardPage.transferLimitInput()).hasValue("150 000");
    }
}
