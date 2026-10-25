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

import static com.codeborne.selenide.Condition.visible;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;
import static com.codeborne.selenide.Selenide.refresh;
import static org.testng.Assert.assertEquals;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900106Test extends CardsHelper {

    @Test(groups = {"@900106"}, dependsOnGroups = {"@900102"})  // сначала убедиться, что лимит вообще меняется
    @Description("TK:@900106, АТ:1900106")
    @TestitStatus(autoTestId = "1900106", autoTestExternalId = "@900106")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Лимит на снятие наличных выше максимального");

        // Подготовка данных
        stand.get(generalUtil.getEnvironmentVariable("env.name"), "stands.yaml");  // Стенд из окружения
        webUser.get("rf_card_mng1", "web_users.yaml");     // Клиентский менеджер

        // Клиент с активной дебетовой картой, лимиты по умолчанию
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

        // =---> Шаг 2: Ввести сумму на 1 ₽ больше максимальной
        setCashLimit("Шаг 2: Ввести лимит 500 001 ₽ и сохранить", cardPage, "500001");
        $x(cardPage.successNotificationXpath).as("Сообщение 'Лимит изменён'").shouldNotBe(visible);
        allureReport.messageWithConsole("Шаг 2: Отображается ошибка 'Превышен максимальный лимит 500 000 ₽'");

        // =---> Шаг 3: Лимит не изменился
        refresh();
        openTab("Шаг 3: Обновить карточку и открыть вкладку 'Лимиты'", "Лимиты");
        assertEquals($x(cardPage.cashLimitInputXpath).getValue(), DEFAULT_CASH_LIMIT, "Лимит после обновления");
    }
}
