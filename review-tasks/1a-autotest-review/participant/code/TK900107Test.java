package ru.rshb.tests.cards.card_block;

import com.codeborne.selenide.Configuration;
import io.qameta.allure.Description;
import io.qameta.allure.Owner;
import lombok.extern.log4j.Log4j2;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import org.testng.annotations.Test;
import ru.rshb.entities.cards.CardInfo;
import ru.rshb.entities.efr_client.EfrClient;
import ru.rshb.pages.NewEfrClientSearchPage;
import ru.rshb.pages.NewEfrLoginPage;
import ru.rshb.pages.cards.CardProfilePage;

import java.util.Map;

import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;
import static org.assertj.core.api.Assertions.assertThat;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900107Test extends CardsHelper {

    @Test(groups = {"@900107"})
    @Description("TK:@900107, АТ:1900107")
    @TestitStatus(autoTestId = "1900107", autoTestExternalId = "@900107")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Просмотр реквизитов карты");

        // Подготовка данных
        stand.get("test2", "stands.yaml");
        webUser.get("rf_m_oper4", "web_users.yaml");     // Менеджер-операционист

        // Клиент с активной дебетовой картой
        EfrClient efrClient = efrApiProcessing.clientCreateWithTelephone(stand, webUser);
        String cardNumber = efrApiProcessing.issueDebitCard(stand, webUser, efrClient.getClientId());
        CardInfo cardInfo = efrApiProcessing.getCardInfo(stand, webUser, cardNumber);

        selenideSetUp();
        Configuration.timeout = 60000;      // Реквизиты на стенде грузятся медленно
        open(stand.getNewEfrApplicationUrl());

        // =---> Подготовка: вход в ЕФР
        allureReport.messageWithConsole("Подготовка: вход в ЕФР. rf_m_oper4");
        new NewEfrLoginPage().login(webUser);
        NewEfrClientSearchPage searchPage = new NewEfrClientSearchPage();

        // =---> Шаг 1: Найти клиента, открыть карту
        CardProfilePage cardPage = openCard("Шаг 1: Найти клиента и открыть карту", searchPage,
                efrClient.getPassportSeries(), efrClient.getPassportNumber(), cardNumber);

        // =---> Шаг 2: Реквизиты совпадают с данными выпуска
        openTab("Шаг 2: Открыть вкладку 'Реквизиты'", "Реквизиты");
        Map<String, String> expectedRequisites = Map.of(
                cardPage.requisiteCardNumberXpath, "•••• " + cardNumber.substring(cardNumber.length() - 4),
                cardPage.requisiteHolderXpath, cardInfo.getHolderName(),
                cardPage.requisiteExpiryXpath, cardInfo.getExpiry(),
                cardPage.requisiteAccountXpath, cardInfo.getAccountNumber()
        );
        for (Map.Entry<String, String> requisite : expectedRequisites.entrySet()) {
            assertThat($x(requisite.getKey()).getText()).isEqualTo(requisite.getValue());
        }
        allureReport.messageWithConsole("Реквизиты карты совпадают с данными выпуска");
    }
}
