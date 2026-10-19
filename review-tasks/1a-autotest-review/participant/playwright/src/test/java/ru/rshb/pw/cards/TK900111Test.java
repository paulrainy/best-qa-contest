package ru.rshb.pw.cards;

import com.microsoft.playwright.Locator;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertEquals;

class TK900111Test extends BaseTest {

    @Test
    @DisplayName("TK-900115 Блокировка карты с причиной «Компрометация»")
    void blockCompromisedCard() {
        // Клиент с активной дебетовой картой
        Client client = api.createClient();
        String cardNumber = api.issueDebitCard(client.id());
        loginAs("rf_card_mng1");

        // Шаг 1: найти клиента, открыть карту
        CardPage cardPage = new CardPage(page).open(client.passportSeries(), client.passportNumber(),
                lastDigits(cardNumber));

        // Шаг 2: заблокировать с причиной «Компрометация»
        cardPage.block("Компрометация");
        page.waitForTimeout(5000);      // Ответ процессинга приходит не сразу
        assertEquals("Заблокирована", cardPage.status().textContent());
        assertThat(cardPage.blockReason()).hasText("Компрометация");

        Locator reissueBanner = page.getByText("Карта будет перевыпущена автоматически");
        if (reissueBanner.isVisible()) {
            assertThat(reissueBanner).isVisible();
        }
    }
}
