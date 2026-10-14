package ru.rshb.tests.cards.card_block;

import io.qameta.allure.Description;
import io.qameta.allure.Owner;
import lombok.extern.log4j.Log4j2;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;
import ru.rshb.entities.efr_client.EfrClient;
import ru.rshb.pages.NewEfrClientSearchPage;
import ru.rshb.pages.NewEfrLoginPage;
import ru.rshb.pages.cards.CardProfilePage;

import static com.codeborne.selenide.Condition.exactText;
import static com.codeborne.selenide.Condition.exactValue;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;
import static com.codeborne.selenide.Selenide.refresh;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900109Test extends CardsHelper {

    @DataProvider(name = "onlineLimits")
    public Object[][] onlineLimits() {
        return new Object[][]{
                {"0", "0"},                 // Нижняя граница: покупки в интернете запрещены
                {"300000", "300 000"}       // Верхняя граница: максимальный лимит
        };
    }

    @Test(groups = {"@900109"}, dataProvider = "onlineLimits")
    @Description("TK:@900109, АТ:1900109")
    @TestitStatus(autoTestId = "1900109", autoTestExternalId = "@900109")
    public void autotest(String limit, String expectedValue) throws Exception {

        allureReport.replaceTestMethodName("Лимит на покупки в интернете: граничные значения");

        // Подготовка данных
        stand.get(generalUtil.getEnvironmentVariable("env.name"), "stands.yaml");  // Стенд из окружения
        webUser.get("rf_card_mng1", "web_users.yaml");     // Клиентский менеджер

        // Клиент с активной дебетовой картой и лимитами по умолчанию — свой на каждую границу
        EfrClient efrClient = efrApiProcessing.clientCreateWithTelephone(stand, webUser);
        String cardNumber = efrApiProcessing.issueDebitCard(stand, webUser, efrClient.getClientId());

        selenideSetUp();
        open(stand.getNewEfrApplicationUrl());

        // =---> Подготовка: вход в ЕФР
        allureReport.messageWithConsole("Подготовка: вход в ЕФР. rf_card_mng1");
        new NewEfrLoginPage().login(webUser);
        NewEfrClientSearchPage searchPage = new NewEfrClientSearchPage();

        // =---> Шаг 1: Найти клиента, открыть карту, вкладку «Лимиты»
        CardProfilePage cardPage = openCard("Шаг 1: Найти клиента и открыть карту", searchPage,
                efrClient.getPassportSeries(), efrClient.getPassportNumber(), cardNumber);
        openTab("Шаг 1: Открыть вкладку 'Лимиты'", "Лимиты");

        // =---> Шаг 2: Установить граничное значение лимита
        allureReport.messageWithConsole("Шаг 2: Установить лимит на покупки в интернете %s ₽".formatted(expectedValue));
        $x(cardPage.onlineLimitInputXpath).setValue(limit);
        $x(cardPage.saveButtonXpath).click();
        $x(cardPage.notificationXpath).as("Сообщение после сохранения").shouldHave(exactText("Лимит изменён"));
        $x(cardPage.onlineLimitInputXpath).as("Поле 'Покупки в интернете, в месяц'")
                .shouldHave(exactValue(expectedValue));

        // =---> Шаг 3: Значение сохранилось
        refresh();
        openTab("Шаг 3: Обновить карточку и открыть вкладку 'Лимиты'", "Лимиты");
        $x(cardPage.onlineLimitInputXpath).as("Поле 'Покупки в интернете, в месяц'")
                .shouldHave(exactValue(expectedValue));
    }
}
