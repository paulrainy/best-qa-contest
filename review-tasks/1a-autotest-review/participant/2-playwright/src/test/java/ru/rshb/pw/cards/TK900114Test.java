package ru.rshb.pw.cards;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.PlaywrightException;
import com.microsoft.playwright.options.AriaRole;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertTrue;

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
        new CardPage(page).open(client.passportSeries(), client.passportNumber(), lastDigits(cardNumber));

        // Шаг 2: открыть вкладку «Реквизиты»
        // Обычный click по вкладке на стенде иногда не срабатывает
        page.getByRole(AriaRole.TAB, new Page.GetByRoleOptions().setName("Реквизиты")).dispatchEvent("click");
        assertTrue(isCardNumberMasked());
        assertThat(page.getByText(cardInfo.holderName()).first()).isVisible();
        assertThat(page.locator("xpath=(//dd)[3]")).hasText(cardInfo.expiry());
    }

    private boolean isCardNumberMasked() {
        try {
            Locator cardNumber = page.getByTestId("requisites").getByTestId("cardNumber");
            cardNumber.waitFor(new Locator.WaitForOptions().setTimeout(5000));
            String text = cardNumber.textContent();
            return text.startsWith("•••• ");
        } catch (PlaywrightException e) {
            return false;
        }
    }
}
