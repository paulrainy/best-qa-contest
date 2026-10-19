package ru.rshb.tests.cards.card_block;

import com.codeborne.selenide.ElementsCollection;
import io.qameta.allure.Description;
import io.qameta.allure.Owner;
import io.qameta.allure.Step;
import lombok.extern.log4j.Log4j2;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import org.testng.annotations.Test;
import ru.rshb.entities.efr_client.EfrClient;
import ru.rshb.pages.NewEfrClientSearchPage;
import ru.rshb.pages.NewEfrLoginPage;
import ru.rshb.pages.cards.CardProfilePage;

import static com.codeborne.selenide.CollectionCondition.size;
import static com.codeborne.selenide.Condition.exactText;
import static com.codeborne.selenide.Condition.not;
import static com.codeborne.selenide.Condition.text;
import static com.codeborne.selenide.Selenide.$$x;
import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;
import static com.codeborne.selenide.Selenide.refresh;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900104Test extends CardsHelper {

    @Test(groups = {"@900104"})
    @Description("TK:@900104, АТ:1900104")
    @TestitStatus(autoTestId = "1900104", autoTestExternalId = "@900104")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Перевыпуск карты при повреждении");

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
        $x(cardPage.cardStatusXpath).as("Статус карты").shouldHave(text("Активна"));

        // =---> Шаг 2: Перевыпустить карту
        reissueCard("Шаг 2: Перевыпустить карту с причиной 'Повреждение'", cardPage, "Повреждение");
        $x(cardPage.notificationXpath).as("Сообщение").shouldHave(exactText("Заявка на перевыпуск создана"));

        // =---> Шаг 3: В профиле старая и новая карты
        allureReport.messageWithConsole("Шаг 3: Обновить продуктовый профиль");
        refresh();
        String newCardDigits = checkReissuedCards(cardNumber);
        waitForCardStatusInProfile("Шаг 3: Старая карта в статусе 'Закрыта'",
                cardNumber.substring(cardNumber.length() - 4), "Закрыта");
        waitForCardStatusInProfile("Шаг 3: Новая карта в статусе 'Заказана'", newCardDigits, "Заказана");
    }

    /**
     * Проверяет, что после перевыпуска в продуктовом профиле две карты.
     *
     * @param oldCardNumber номер перевыпущенной карты
     * @return последние 4 цифры новой карты
     */
    @Step("Проверить, что в профиле две карты")
    private String checkReissuedCards(String oldCardNumber) {
        String oldDigits = oldCardNumber.substring(oldCardNumber.length() - 4);

        ElementsCollection cardRows = $$x("//div[@data-id='productProfile']//tr[@data-id='cardRow']");
        cardRows.as("Карты в продуктовом профиле").shouldHave(size(2));

        String newCardNumber = cardRows.filterBy(not(text(oldDigits))).first()
                .$x(".//td[@data-id='cardNumber']").getText();
        return newCardNumber.substring(newCardNumber.length() - 4);
    }
}
