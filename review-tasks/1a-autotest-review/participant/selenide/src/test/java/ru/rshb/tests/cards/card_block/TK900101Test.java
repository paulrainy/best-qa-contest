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

import static com.codeborne.selenide.Selenide.open;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900101Test extends CardsHelper {

    @Test(groups = {"@900101"})
    @Description("TK:@900101, АТ:1900101")
    @TestitStatus(autoTestId = "1900101", autoTestExternalId = "@900101")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Блокировка карты по заявлению клиента");

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
        checkCardStatus("Шаг 1: Статус карты 'Активна'", cardPage, "Активна");

        // =---> Шаг 2: Заблокировать карту
        blockCard("Шаг 2: Заблокировать карту с причиной 'Утеря'", cardPage, "Утеря");
        checkCardStatus("Шаг 2: Статус карты 'Заблокирована'", cardPage, "Заблокирована");
        checkButtonDisplayed("Шаг 2: Отображается кнопка 'Разблокировать'", "Разблокировать");
        blockedCardClient = efrClient;
        blockedCardNumber = cardNumber;

        // =---> Шаг 3: Запись в истории
        checkHistoryRecord("Шаг 3: В истории есть запись 'Блокировка карты'", cardPage, "Блокировка карты");
    }
}
