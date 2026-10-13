package ru.rshb.tests;

import com.codeborne.selenide.Configuration;
import com.codeborne.selenide.Selenide;
import com.codeborne.selenide.logevents.SelenideLogger;
import io.qameta.allure.selenide.AllureSelenide;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.testng.AbstractTestNGSpringContextTests;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeSuite;
import ru.rshb.playground.efr.EfrStubServer;
import ru.rshb.utils.AllureReport;
import ru.rshb.utils.GeneralUtil;
import ru.rshb.utils.YandexBrowser;

import java.nio.file.Path;
import java.util.Optional;

@ContextConfiguration(classes = PlaygroundConfig.class)
public class BaseTest extends AbstractTestNGSpringContextTests {

    protected AllureReport allureReport = new AllureReport();
    protected GeneralUtil generalUtil = new GeneralUtil();

    /**
     * Поднимает заглушку ЕФР, если она ещё не запущена отдельно через mvn exec:java.
     */
    @BeforeSuite(alwaysRun = true)
    public void startEfrStub() {
        EfrStubServer.startIfNotRunning();
    }

    /**
     * Настройки браузера. Остальное (например, -Dselenide.headless=true) Selenide берёт из системных свойств.
     */
    public void selenideSetUp() {
        // Драйвер Chrome Selenium скачивает в папку проекта, а не в домашнюю папку пользователя
        if (System.getProperty("SE_CACHE_PATH") == null) {
            System.setProperty("SE_CACHE_PATH", Path.of(".selenium").toAbsolutePath().toString());
        }
        Configuration.browser = "chrome";
        useYandexBrowserIfInstalled();
        Configuration.browserSize = "1600x1000";
        Configuration.reportsFolder = "target/selenide-reports";
        Configuration.downloadsFolder = "target/downloads";
        SelenideLogger.addListener("AllureSelenide", new AllureSelenide().screenshots(true).savePageSource(false));
    }

    /**
     * По умолчанию тесты идут в Яндекс Браузере, если он установлен: на ВДИ компании запуск Chrome запрещён.
     * -Dbrowser=chrome — запустить в Chrome, -Dbrowser=yandex — только в Яндекс Браузере.
     */
    private void useYandexBrowserIfInstalled() {
        String browser = System.getProperty("browser", "auto");
        if (browser.equals("chrome")) {
            return;
        }
        Optional<Path> yandex = YandexBrowser.findBinary();
        if (yandex.isEmpty()) {
            if (browser.equals("yandex")) {
                throw new IllegalStateException("Яндекс Браузер не найден. Укажите путь к нему: -Dyandex.binary=...");
            }
            return;
        }
        Configuration.browserBinary = yandex.get().toString();
        System.setProperty("webdriver.chrome.driver", YandexBrowser.driverFor(yandex.get()));
    }

    @AfterMethod(alwaysRun = true)
    public void closeBrowser() {
        Selenide.closeWebDriver();
    }
}
