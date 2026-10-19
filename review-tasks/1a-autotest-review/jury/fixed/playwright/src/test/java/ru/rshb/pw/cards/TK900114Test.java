package ru.rshb.pw.cards;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.regex.Pattern;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

class TK900114Test extends BaseTest {

    @Test
    @DisplayName("TK-900114 Номер карты в реквизитах маскирован")
    void cardNumberIsMasked() {
        // Клиент с активной дебетовой картой
        Client client = api.createClient();
        String cardNumber = api.issueDebitCard(client.id());
        CardInfo cardInfo = api.getCardInfo(cardNumber);
        loginAs("rf_m_oper4");

        // Шаг 1: найти клиента, открыть карту
        CardPage cardPage = new CardPage(page).open(client.passportSeries(), client.passportNumber(),
                lastDigits(cardNumber));

        // Шаг 2: открыть вкладку «Реквизиты»
        cardPage.openTab("Реквизиты");
        assertThat(cardPage.requisite("cardNumber")).hasText(Pattern.compile("^•••• " + lastDigits(cardNumber) + "$"));
        assertThat(cardPage.requisite("holder")).hasText(cardInfo.holderName());
        assertThat(cardPage.requisite("expiry")).hasText(cardInfo.expiry());
    }
}
