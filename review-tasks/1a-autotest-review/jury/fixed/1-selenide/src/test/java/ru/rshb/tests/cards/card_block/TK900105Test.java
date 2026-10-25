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

import static com.codeborne.selenide.Condition.exactText;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900105Test extends CardsHelper {

    @Test(groups = {"@900105"})
    @Description("TK:@900105, АТ:1900105")
    @TestitStatus(autoTestId = "1900105", autoTestExternalId = "@900105")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Смена ПИН-кода недоступна для заблокированной карты");

        // Подготовка данных
        stand.get(generalUtil.getEnvironmentVariable("env.name"), "stands.yaml");  // Стенд из окружения
        webUser.get("rf_card_mng1", "web_users.yaml");     // Клиентский менеджер

        // Клиент с заблокированной дебетовой картой
        EfrClient efrClient = efrApiProcessing.clientCreateWithTelephone(stand, webUser);
        String cardNumber = efrApiProcessing.issueDebitCard(stand, webUser, efrClient.getClientId());
        efrApiProcessing.blockCard(stand, webUser, cardNumber, "Утеря");

        selenideSetUp();
        open(stand.getNewEfrApplicationUrl());

        // =---> Подготовка: вход в ЕФР
        allureReport.messageWithConsole("Подготовка: вход в ЕФР. rf_card_mng1");
        new NewEfrLoginPage().login(webUser);
        NewEfrClientSearchPage searchPage = new NewEfrClientSearchPage();

        // =---> Шаг 1: Найти клиента, открыть заблокированную карту
        CardProfilePage cardPage = openCard("Шаг 1: Найти клиента и открыть заблокированную карту", searchPage,
                efrClient.getPassportSeries(), efrClient.getPassportNumber(), cardNumber);
        $x(cardPage.cardStatusXpath).as("Статус карты").shouldHave(exactText("Заблокирована"));

        // =---> Шаг 2: Смена ПИН-кода недоступна
        checkPinChangeUnavailable("Шаг 2: Пункт 'Сменить ПИН-код' в меню 'Действия' недоступен", cardPage);
    }
}
