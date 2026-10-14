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
import static com.codeborne.selenide.Condition.text;
import static com.codeborne.selenide.Condition.visible;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900108Test extends CardsHelper {

    @Test(groups = {"@900108"})
    @Description("TK:@900108, АТ:1900108")
    @TestitStatus(autoTestId = "1900108", autoTestExternalId = "@900108")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Разблокировка без подтверждения старшего менеджера");

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
        // Ошибку окно подтверждения показывает у себя, а не во всплывающем сообщении
        $x("//div[@role='dialog']//div[@data-id='dialogError']").as("Ошибка в окне подтверждения")
                .shouldHave(exactText("Требуется подтверждение старшего менеджера"));
        $x(cardPage.successNotificationXpath).as("Сообщение 'Карта разблокирована'").shouldNotBe(visible);

        // =---> Шаг 3: Закрыть окно подтверждения
        $x(cardPage.cancelButtonXpath).click();
        $x("//div[@role='dialog']").as("Окно подтверждения").shouldNotBe(visible);
        checkCardStatus("Шаг 3: Статус карты 'Заблокирована'", cardPage, "Заблокирована");
    }
}
