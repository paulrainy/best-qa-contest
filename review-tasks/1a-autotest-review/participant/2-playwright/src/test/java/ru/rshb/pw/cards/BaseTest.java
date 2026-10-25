package ru.rshb.pw.cards;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.BrowserType;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import com.microsoft.playwright.Tracing;
import com.microsoft.playwright.options.AriaRole;
import io.qameta.allure.Step;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.TestInfo;

import java.nio.file.Paths;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public abstract class BaseTest {

    // Браузер один на все тесты класса: запуск дорогой, а состояния у него нет
    protected static Playwright playwright;
    protected static Browser browser;

    // Контекст и страница — свои у каждого теста
    protected BrowserContext context;
    protected Page page;
    protected CardsApi api;

    @BeforeAll
    static void launchBrowser() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch(new BrowserType.LaunchOptions().setHeadless(Config.headless()).setExecutablePath(Config.browserPath()));
    }

    @AfterAll
    static void closeBrowser() {
        playwright.close();
    }

    @BeforeEach
    void createContext() {
        context = browser.newContext(new Browser.NewContextOptions().setBaseURL(Config.baseUrl()));
        context.tracing().start(new Tracing.StartOptions().setScreenshots(true).setSnapshots(true));
        page = context.newPage();
        api = new CardsApi(Config.apiUrl(), Config.apiToken());
    }

    @AfterEach
    void closeContext(TestInfo testInfo) {
        context.tracing().stop(new Tracing.StopOptions()
                .setPath(Paths.get("build/traces", testInfo.getDisplayName() + ".zip")));
        context.close();
    }

    @Step("Войти в ЕФР под ролью {role}")
    protected void loginAs(String role) {
        User user = Config.user(role);
        page.navigate("/efr/");
        page.getByLabel("Логин").fill(user.login());
        page.getByLabel("Пароль").fill(user.password());
        page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Войти")).click();
        assertThat(page.getByTestId("clientSearch")).isVisible();
    }

    protected static String lastDigits(String cardNumber) {
        return cardNumber.substring(cardNumber.length() - 4);
    }
}
