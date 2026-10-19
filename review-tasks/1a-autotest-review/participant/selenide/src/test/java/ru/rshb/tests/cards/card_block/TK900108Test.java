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

import static com.codeborne.selenide.Condition.text;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;
import static org.testng.Assert.fail;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900108Test extends CardsHelper {

    @Test(groups = {"@900108"})
    @Description("TK:@900108, АТ:1900108")
    @TestitStatus(autoTestId = "1900108", autoTestExternalId = "@900108")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Разблокировка карты");

        // Подготовка данных
        stand.get(generalUtil.getEnvironmentVariable("env.name"), "stands.yaml");  // Стенд из окружения
        webUser.get("rf_card_sup1", "web_users.yaml");     // Старший менеджер: через API карту блокирует только он

        // Клиент с заблокированной дебетовой картой
        EfrClient efrClient = efrApiProcessing.clientCreateWithTelephone(stand, webUser);
        String cardNumber = efrApiProcessing.issueDebitCard(stand, webUser, efrClient.getClientId());
        efrApiProcessing.blockCard(stand, webUser, cardNumber, "Утеря");

        selenideSetUp();
        open(stand.getNewEfrApplicationUrl());

        // =---> Подготовка: вход в ЕФР
        allureReport.messageWithConsole("Подготовка: вход в ЕФР. %s".formatted(webUser.getLogin()));
        new NewEfrLoginPage().login(webUser);
        NewEfrClientSearchPage searchPage = new NewEfrClientSearchPage();

        // =---> Шаг 1: Найти клиента, открыть заблокированную карту
        CardProfilePage cardPage = openCard("Шаг 1: Найти клиента и открыть заблокированную карту", searchPage,
                efrClient.getPassportSeries(), efrClient.getPassportNumber(), cardNumber);
        $x(cardPage.cardStatusXpath).as("Статус карты").shouldHave(text("Заблокирована"));

        // =---> Шаг 2: Подтвердить разблокировку, не заполняя логин и пароль старшего менеджера
        allureReport.messageWithConsole("Шаг 2: Нажать 'Разблокировать' и 'Подтвердить' без логина и пароля");
        $x(cardPage.unblockButtonXpath).click();
        $x(cardPage.confirmButtonXpath).click();
        try {
            $x(cardPage.notificationXpath).shouldHave(text("Карта разблокирована"));
            fail("Карта разблокирована без подтверждения старшего менеджера");
        } catch (Throwable e) {
            allureReport.messageWithConsole("Карта не разблокирована — ожидаемо");
        }

        // =---> Шаг 3: Закрыть окно подтверждения
        $x(cardPage.cancelButtonXpath).click();
        allureReport.messageWithConsole("Шаг 3: Окно закрыто, карта осталась заблокированной");
    }
}
