package ru.rshb.tests.cards.card_block;

import io.qameta.allure.Description;
import io.qameta.allure.Owner;
import lombok.extern.log4j.Log4j2;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import org.testng.annotations.Test;
import ru.rshb.entities.efr_client.EfrClient;
import ru.rshb.pages.NewEfrClientSearchPage;
import ru.rshb.pages.NewEfrLoginPage;
import ru.rshb.pages.cards.CardProfilePage;

import static com.codeborne.selenide.CollectionCondition.size;
import static com.codeborne.selenide.CollectionCondition.sizeGreaterThan;
import static com.codeborne.selenide.Condition.text;
import static com.codeborne.selenide.Condition.visible;
import static com.codeborne.selenide.Selenide.$$x;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900110Test extends CardsHelper {

    @Test(groups = {"@900110"})
    @Description("TK:@900110, АТ:1900110")
    @TestitStatus(autoTestId = "1900110", autoTestExternalId = "@900110")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Отмена блокировки карты в окне подтверждения");

        // Подготовка данных
        stand.get(generalUtil.getEnvironmentVariable("env.name"), "stands.yaml");  // Стенд из окружения
        webUser.setLogin("ivanov_ii");                  // У rf_card_mng1 на test3 слетели права,
        webUser.setPassword("Iv@nov_2026");             // пока хожу под своей учёткой

        // Клиент с активной дебетовой картой
        EfrClient efrClient = efrApiProcessing.clientCreateWithTelephone(stand, webUser);
        String cardNumber = efrApiProcessing.issueDebitCard(stand, webUser, efrClient.getClientId());

        selenideSetUp();
        open(stand.getNewEfrApplicationUrl());

        // =---> Подготовка: вход в ЕФР
        allureReport.messageWithConsole("Подготовка: вход в ЕФР. %s".formatted(webUser.getLogin()));
        new NewEfrLoginPage().login(webUser);
        NewEfrClientSearchPage searchPage = new NewEfrClientSearchPage();

        // =---> Шаг 1: Найти клиента, открыть карту
        CardProfilePage cardPage = openCard("Шаг 1: Найти клиента и открыть карту", searchPage,
                efrClient.getPassportSeries(), efrClient.getPassportNumber(), cardNumber);
        $x(cardPage.cardStatusXpath).as("Статус карты").shouldHave(text("Активна"));

        // =---> Шаг 2: Начать блокировку и отменить её
        allureReport.messageWithConsole("Шаг 2: Нажать 'Заблокировать', выбрать причину 'Утеря', нажать 'Отмена'");
        $x(cardPage.blockButtonXpath).click();
        $x(cardPage.blockReasonSelectXpath).selectOptionContainingText("Утеря");
        $x(cardPage.cancelButtonXpath).click();
        $x(cardPage.blockDialogXpath).as("Окно блокировки").shouldNotBe(visible);
        $x(cardPage.cardStatusXpath).as("Статус карты").shouldHave(text("Активна"));
        checkButtonDisplayed("Шаг 2: Отображается кнопка 'Заблокировать'", "Заблокировать");

        // =---> Шаг 3: В истории нет записи о блокировке
        allureReport.messageWithConsole("Шаг 3: Открыть вкладку 'История'");
        $x(cardPage.historyTabXpath).click();
        $$x(cardPage.historyRowXpath).as("Записи истории").shouldHave(sizeGreaterThan(0));
        $$x(cardPage.historyRowXpath + "[contains(., 'Блокировка карты')]")
                .as("Записи 'Блокировка карты'")
                .shouldHave(size(0));
    }
}
