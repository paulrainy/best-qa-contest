package ru.rshb.tests.cards.card_block;

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

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static com.codeborne.selenide.Condition.exactText;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900107Test extends CardsHelper {

    @Test(groups = {"@900107"})
    @Description("TK:@900107, АТ:1900107")
    @TestitStatus(autoTestId = "1900107", autoTestExternalId = "@900107")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Просмотр реквизитов карты");

        // Подготовка данных
        stand.get(generalUtil.getEnvironmentVariable("env.name"), "stands.yaml");  // Стенд из окружения
        webUser.get("rf_m_oper4", "web_users.yaml");     // Менеджер-операционист

        // Клиент с активной дебетовой картой
        EfrClient efrClient = efrApiProcessing.clientCreateWithTelephone(stand, webUser);
        String cardNumber = efrApiProcessing.issueDebitCard(stand, webUser, efrClient.getClientId());
        CardInfo cardInfo = efrApiProcessing.getCardInfo(stand, webUser, cardNumber);

        selenideSetUp();
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
        // Название поля -> (xpath, ожидаемое значение)
        Map<String, List<String>> expectedRequisites = new LinkedHashMap<>();
        expectedRequisites.put("Номер карты", List.of(cardPage.requisiteCardNumberXpath,
                "•••• " + cardNumber.substring(cardNumber.length() - 4)));
        expectedRequisites.put("Держатель", List.of(cardPage.requisiteHolderXpath, cardInfo.getHolderName()));
        expectedRequisites.put("Срок действия", List.of(cardPage.requisiteExpiryXpath, cardInfo.getExpiry()));
        expectedRequisites.put("Номер счёта", List.of(cardPage.requisiteAccountXpath, cardInfo.getAccountNumber()));
        expectedRequisites.forEach((name, xpathAndValue) ->
                $x(xpathAndValue.get(0)).as(name).shouldHave(exactText(xpathAndValue.get(1))));
        allureReport.messageWithConsole("Реквизиты карты совпадают с данными выпуска");
    }
}
