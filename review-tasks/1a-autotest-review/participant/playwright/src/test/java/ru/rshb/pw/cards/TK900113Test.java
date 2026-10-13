package ru.rshb.pw.cards;

import com.microsoft.playwright.Browser;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInfo;
import org.junit.jupiter.api.TestInstance;
import org.junit.jupiter.api.TestMethodOrder;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
@DisplayName("TK-900113 Временная блокировка карты и её снятие")
class TK900113Test extends BaseTest {

    private Client client;
    private String cardNumber;
    private CardPage cardPage;

    // Шаги кейса — отдельные тесты, чтобы в отчёте было видно, на каком шаге упало.
    // Поэтому контекст и страница общие на весь класс, а не свои у каждого теста.
    @BeforeAll
    void openSharedPage() {
        context = browser.newContext(new Browser.NewContextOptions().setBaseURL(Config.baseUrl()));
        page = context.newPage();
        api = new CardsApi(Config.apiUrl(), Config.apiToken());
    }

    @Override
    void createContext() {
    }

    @Override
    void closeContext(TestInfo testInfo) {
    }

    @AfterAll
    void closeSharedPage() {
        context.close();
    }

    @Test
    @Order(1)
    @DisplayName("Шаг 1: открыть активную карту")
    void openActiveCard() {
        client = api.createClient();
        cardNumber = api.issueDebitCard(client.id());
        loginAs("rf_card_mng1");

        cardPage = new CardPage(page).open(client.passportSeries(), client.passportNumber(), lastDigits(cardNumber));
        assertThat(cardPage.status()).hasText("Активна");
    }

    @Test
    @Order(2)
    @DisplayName("Шаг 2: временно заблокировать карту")
    void blockTemporarily() {
        cardPage.blockTemporarily();
        assertThat(cardPage.status()).hasText("Временно заблокирована");
    }

    @Test
    @Order(3)
    @DisplayName("Шаг 3: снять временную блокировку")
    void removeTemporaryBlock() {
        cardPage.removeTemporaryBlock();
        assertThat(cardPage.status()).hasText("Активна");
    }
}
