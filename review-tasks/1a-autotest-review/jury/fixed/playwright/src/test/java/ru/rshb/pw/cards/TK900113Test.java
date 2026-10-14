package ru.rshb.pw.cards;

import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.AriaRole;
import io.qameta.allure.Allure;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

class TK900113Test extends BaseTest {

    @Test
    @DisplayName("TK-900113 Временная блокировка карты и её снятие")
    void blockTemporarilyAndRemove() {
        // Клиент с активной дебетовой картой
        Client client = api.createClient();
        String cardNumber = api.issueDebitCard(client.id());
        loginAs("rf_card_mng1");
        CardPage cardPage = new CardPage(page);

        Allure.step("Шаг 1: открыть активную карту", () -> {
            cardPage.open(client.passportSeries(), client.passportNumber(), lastDigits(cardNumber));
            assertThat(cardPage.status()).hasText("Активна");
        });

        Allure.step("Шаг 2: временно заблокировать карту", () -> {
            cardPage.blockTemporarily();
            assertThat(cardPage.status()).hasText("Временно заблокирована");
            assertThat(page.getByRole(AriaRole.BUTTON,
                    new Page.GetByRoleOptions().setName("Снять временную блокировку"))).isVisible();
        });

        Allure.step("Шаг 3: снять временную блокировку", () -> {
            cardPage.removeTemporaryBlock();
            assertThat(cardPage.status()).hasText("Активна");
        });
    }
}
