package ru.rshb.tests.cards.card_block;

import io.qameta.allure.Description;
import io.qameta.allure.Owner;
import lombok.extern.log4j.Log4j2;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import org.testng.annotations.Test;
import ru.rshb.pages.NewEfrClientSearchPage;
import ru.rshb.pages.NewEfrLoginPage;
import ru.rshb.pages.cards.CardProfilePage;

import static com.codeborne.selenide.Selenide.$x;
import static com.codeborne.selenide.Selenide.open;
import static com.codeborne.selenide.Selenide.refresh;

@Log4j2
@Owner("Иванов Иван Иванович")
public class TK900103Test extends CardsHelper {

    @Test(groups = {"@900103"})
    @Description("TK:@900103, АТ:1900103")
    @TestitStatus(autoTestId = "1900103", autoTestExternalId = "@900103")
    public void autotest() throws Exception {

        allureReport.replaceTestMethodName("Разблокировка карты");

        // Подготовка данных
        webUser.get("rf_card_mng1", "web_users.yaml");     // Клиентский менеджер

        selenideSetUp();
        open("http://localhost:18080/efr/");

        // =---> Подготовка: вход в ЕФР
        allureReport.messageWithConsole("Подготовка: вход в ЕФР. rf_card_mng1");
        new NewEfrLoginPage().login(webUser);
        NewEfrClientSearchPage searchPage = new NewEfrClientSearchPage();

        // =---> Шаг 1: Найти клиента, открыть заблокированную карту
        CardProfilePage cardPage = openCard("Шаг 1: Найти клиента и открыть заблокированную карту", searchPage,
                TK900101Test.blockedCardClient.getPassportSeries(), TK900101Test.blockedCardClient.getPassportNumber(),
                TK900101Test.blockedCardNumber);

        // =---> Шаг 2: Разблокировать карту
        unblockCard("Шаг 2: Разблокировать карту с подтверждением старшего менеджера", cardPage,
                "rf_card_sup1", "Kart0chka#2026");
        while (!$x(cardPage.cardStatusXpath).getText().equals("Активна")) {
            refresh();      // ждём, пока процессинг применит разблокировку
        }
        checkCardStatus("Шаг 2: Статус карты 'Активна'", cardPage, "Активна");
        checkButtonDisplayed("Шаг 2: Отображается кнопка 'Заблокировать'", "Заблокировать");
    }
}
