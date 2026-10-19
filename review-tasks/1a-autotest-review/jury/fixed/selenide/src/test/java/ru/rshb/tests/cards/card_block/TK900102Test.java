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

import static com.codeborne.selenide.Condition.exactValue;
import static com.codeborne.selenide.Condition.text;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900102Test extends CardsHelper {

    @Test(groups = {"@900102"})
    @Description("TK:@900102, АТ:1900102")
    @TestitStatus(autoTestId = "1900102", autoTestExternalId = "@900102")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Изменение лимита на снятие наличных");

        // Подготовка данных
        stand.get(generalUtil.getEnvironmentVariable("env.name"), "stands.yaml");  // Стенд из окружения
        webUser.get("rf_card_mng1", "web_users.yaml");     // Клиентский менеджер

        // Клиент с активной дебетовой картой
        EfrClient efrClient = efrApiProcessing.clientCreateWithTelephone(stand, webUser);
        String cardNumber = efrApiProcessing.issueDebitCard(stand, webUser, efrClient.getClientId());

        selenideSetUp();
        open(stand.getNewEfrApplicationUrl());

        // =---> Подготовка: вход в ЕФР
        allureReport.messageWithConsole("Подготовка: вход в ЕФР. rf_card_mng1");
        new NewEfrLoginPage().login(webUser);
        NewEfrClientSearchPage searchPage = new NewEfrClientSearchPage();

        // =---> Шаг 1: Найти клиента, открыть карту
        CardProfilePage cardPage = openCard("Шаг 1: Найти клиента и открыть карту", searchPage,
                efrClient.getPassportSeries(), efrClient.getPassportNumber(), cardNumber);

        // =---> Шаг 2: Установить лимит
        setCashLimit("Шаг 2: Установить лимит на снятие наличных 50 000 ₽", cardPage, "50000");

        // =---> Шаг 2: Лимит сохранён
        $x(cardPage.successNotificationXpath).as("Сообщение 'Лимит изменён'").shouldHave(text("Лимит изменён"));
        $x(cardPage.cashLimitInputXpath).as("Поле 'Снятие наличных, в месяц'").shouldHave(exactValue("50 000"));
        allureReport.messageWithConsole("Шаг 2: Лимит сохранён, отображается сообщение 'Лимит изменён'");
    }
}
