package ru.rshb.pw.cards;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Response;
import com.microsoft.playwright.options.AriaRole;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TK900115Test extends BaseTest {

    @Test
    @DisplayName("TK-900115 Закрытие карты с нулевым остатком")
    void closeCardWithZeroBalance() {
        // Клиент с новой дебетовой картой: остаток 0
        Client client = api.createClient();
        String cardNumber = api.issueDebitCard(client.id());
        loginAs("rf_card_mng1");

        // Шаг 1: найти клиента, открыть карту
        CardPage cardPage = new CardPage(page).open(client.passportSeries(), client.passportNumber(),
                lastDigits(cardNumber));
        assertThat(cardPage.status()).hasText("Активна");
        assertThat(cardPage.balance()).containsText("0,00");

        // Шаг 2: в меню «Действия» выбрать «Закрыть карту»
        page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Действия")).click();
        page.getByRole(AriaRole.MENUITEM, new Page.GetByRoleOptions().setName("Закрыть карту"))
                .click(new Locator.ClickOptions().setForce(true));
        Locator dialog = page.getByRole(AriaRole.DIALOG);
        assertThat(dialog).containsText("Закрыть карту *" + lastDigits(cardNumber) + "?");

        // Шаг 3: подтвердить закрытие — ждём ответ сервиса закрытия
        Response response = page.waitForResponse(r -> r.url().contains("/api/cards/close"),
                () -> dialog.getByRole(AriaRole.BUTTON, new Locator.GetByRoleOptions().setName("Подтвердить")).click());
        assertTrue(response.ok());

        assertThat(dialog).isHidden();
        assertThat(cardPage.status()).hasText("Закрыта");
        assertThat(cardPage.notification()).hasText("Карта закрыта");

        // Шаг 4: открыть вкладку «История»
        page.reload();      // История подтягивается только после обновления страницы
        cardPage.openTab("История");
        assertThat(page.getByTestId("history")).isVisible();
    }
}
