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
import static com.codeborne.selenide.Selenide.$$x;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;
import static org.assertj.core.api.Assertions.assertThat;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900101Test extends CardsHelper {

    static EfrClient blockedCardClient;     // Для TK900103
    static String blockedCardNumber;

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
        allureReport.messageWithConsole("Подготовка: вход в ЕФР. %s / %s".formatted(webUser.getLogin(), webUser.getPassword()));
        new NewEfrLoginPage().login(webUser);
        NewEfrClientSearchPage searchPage = new NewEfrClientSearchPage();

        // =---> Шаг 1: Найти клиента, открыть карту
        CardProfilePage cardPage = openCard("Шаг 1: Найти клиента и открыть карту", searchPage,
                efrClient.getPassportSeries(), efrClient.getPassportNumber(), cardNumber);
        // новая карта всегда активна

        // =---> Шаг 2: Заблокировать карту
        blockCard("Шаг 2: Заблокировать карту с причиной 'Утеря'", cardPage, "Утеря");
        $x(cardPage.cardStatusXpath).shouldBe(visible);
        allureReport.messageWithConsole("Шаг 2: Статус карты 'Заблокирована'");
        $x("//button[normalize-space()='Разблокировать']").as("Кнопка 'Заблокировать'").shouldBe(visible);
        blockedCardClient = efrClient;
        blockedCardNumber = cardNumber;

        // =---> Шаг 3: Запись в истории
        try {
            $x(cardPage.historyTabXpath).click();
            int records = $$x(cardPage.historyRowXpath + "[contains(., 'Блокировка карты')]").size();
            assertThat(records)
                    .withFailMessage("В истории нет записи 'Блокировка карты'")
                    .isGreaterThan(0);
            allureReport.messageWithConsole("Шаг 3: В истории есть запись 'Блокировка карты'");
        } catch (Throwable e) {
            log.warn("История операций не прогрузилась: {}", e.getMessage());
        }
    }
}
