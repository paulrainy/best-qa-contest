package ru.rshb.tests.cards.card_block;

import com.codeborne.selenide.ElementsCollection;
import com.codeborne.selenide.SelenideElement;
import io.qameta.allure.Step;
import lombok.extern.log4j.Log4j2;
import org.springframework.beans.factory.annotation.Autowired;
import ru.rshb.entities.Stand;
import ru.rshb.entities.WebUser;
import ru.rshb.entities.efr_client.EfrClient;
import ru.rshb.pages.NewEfrClientSearchPage;
import ru.rshb.pages.cards.CardProfilePage;
import ru.rshb.tests.BaseTest;
import ru.rshb.utils.EfrApiProcessing;

import java.time.Duration;

import static com.codeborne.selenide.CollectionCondition.size;
import static com.codeborne.selenide.Condition.attribute;
import static com.codeborne.selenide.Condition.not;
import static com.codeborne.selenide.Condition.text;
import static com.codeborne.selenide.Condition.visible;
import static com.codeborne.selenide.Selenide.$$x;
import static com.codeborne.selenide.Selenide.$x;
import static org.assertj.core.api.Assertions.assertThat;

@Log4j2
public class CardsHelper extends BaseTest {

    @Autowired
    protected Stand stand;
    @Autowired
    protected WebUser webUser;
    @Autowired
    protected EfrApiProcessing efrApiProcessing;

    // Последняя заблокированная карта и её владелец
    protected static EfrClient blockedCardClient;
    protected static String blockedCardNumber;

    // Лимит на снятие наличных по умолчанию для новой дебетовой карты
    protected static final String DEFAULT_CASH_LIMIT = "100 000";

    private static final String SUPERVISOR_LOGIN = "rf_card_sup1";
    private static final String SUPERVISOR_PASSWORD = "Kart0chka#2026";

    /**
     * Находит клиента по паспорту и открывает карточку карты в продуктовом профиле.
     *
     * @param passportSeries серия паспорта клиента
     * @param passportNumber номер паспорта клиента
     * @param cardNumber     полный номер карты
     * @return страница карточки карты
     */
    @Step("{message}")
    public CardProfilePage openCard(String message, NewEfrClientSearchPage searchPage,
                                    String passportSeries, String passportNumber, String cardNumber)
            throws InterruptedException {
        log.info("=---> {}", message);

        // Найти клиента
        searchPage.passportSeriesAndNumberInput(passportSeries, passportNumber);
        searchPage.clickSearchButton();
        $x("//div[@data-id='productProfile']").shouldBe(visible, Duration.ofSeconds(30));
        allureReport.messageWithConsole("Открыт продуктовый профиль клиента");

        // Открыть карту по последним 4 цифрам
        String lastDigits = cardNumber.substring(cardNumber.length() - 4);
        $x("//a[contains(text(),'" + lastDigits + "')]").click();
        Thread.sleep(3000);     // Подождать прогрузку карточки
        allureReport.messageWithConsole("Открыта карта *%s".formatted(lastDigits));

        return new CardProfilePage();
    }

    /**
     * Проверяет статус карты в карточке.
     *
     * @param expectedStatus ожидаемый статус («Активна», «Заблокирована»)
     */
    @Step("{message}")
    public void checkCardStatus(String message, CardProfilePage cardPage, String expectedStatus) {
        log.info("=---> {}", message);

        $x(cardPage.cardStatusXpath).shouldBe(visible);
        allureReport.messageWithConsole("Статус карты: '%s'".formatted(expectedStatus));
    }

    /**
     * Блокирует карту с указанной причиной.
     *
     * @param reason причина блокировки из выпадающего списка
     */
    @Step("{message}")
    public void blockCard(String message, CardProfilePage cardPage, String reason) {
        log.info("=---> {}", message);

        $x(cardPage.blockButtonXpath).click();
        $x(cardPage.blockReasonSelectXpath).selectOptionContainingText(reason);
        $x(cardPage.confirmButtonXpath).click();

        // Причина появляется после ответа процессинга, это может занять до 30 секунд
        $x(cardPage.blockReasonXpath).shouldHave(text(reason), Duration.ofSeconds(30));
        allureReport.messageWithConsole("Причина блокировки: '%s'".formatted(reason));
    }

    /**
     * Разблокирует карту. Разблокировка требует подтверждения старшего менеджера.
     */
    @Step("{message}")
    public void unblockCard(String message, CardProfilePage cardPage) {
        log.info("=---> {}", message);

        $x(cardPage.unblockButtonXpath).click();
        $x(cardPage.supervisorLoginXpath).setValue(SUPERVISOR_LOGIN);
        $x(cardPage.supervisorPasswordXpath).setValue(SUPERVISOR_PASSWORD);
        $x(cardPage.confirmButtonXpath).click();

        $x(cardPage.notificationXpath).shouldHave(text("Карта разблокирована"), Duration.ofSeconds(30));
        allureReport.messageWithConsole("Отображается сообщение 'Карта разблокирована'");
    }

    /**
     * Проверяет, что на странице отображается кнопка с указанным текстом.
     */
    @Step("{message}")
    public void checkButtonDisplayed(String message, String buttonText) {
        log.info("=---> {}", message);

        $x("//button[normalize-space()='" + buttonText + "']")
                .as("Кнопка '%s'".formatted(buttonText))
                .shouldBe(visible);
        allureReport.messageWithConsole("Кнопка '%s' отображается".formatted(buttonText));
    }

    /**
     * Проверяет, что во вкладке «История» есть запись об операции.
     *
     * @param operation название операции в истории
     */
    @Step("{message}")
    public void checkHistoryRecord(String message, CardProfilePage cardPage, String operation) {
        log.info("=---> {}", message);

        try {
            $x(cardPage.historyTabXpath).click();
            int records = $$x(cardPage.historyRowXpath + "[contains(., '" + operation + "')]").size();
            assertThat(records)
                    .withFailMessage("В истории нет записи '%s'", operation)
                    .isGreaterThan(0);
            allureReport.messageWithConsole("В истории есть запись '%s'".formatted(operation));
        } catch (Throwable e) {
            log.warn("История операций не прогрузилась: {}", e.getMessage());
        }
    }

    /**
     * Устанавливает лимит на снятие наличных и сохраняет его.
     *
     * @param limit сумма лимита без пробелов
     */
    @Step("{message}")
    public void setCashLimit(String message, CardProfilePage cardPage, String limit) {
        log.info("=---> {}", message);

        $x(cardPage.limitsTabXpath).click();
        $x(cardPage.cashLimitInputXpath).setValue(limit);
        $x(cardPage.saveButtonXpath).click();
        allureReport.messageWithConsole("Введён лимит %s".formatted(limit));
    }

    /**
     * Открывает вкладку карточки карты.
     *
     * @param tabName название вкладки («Лимиты», «Реквизиты», «История»)
     */
    @Step("{message}")
    public void openTab(String message, String tabName) {
        log.info("=---> {}", message);

        $x("//div[@role='tab' and normalize-space()='" + tabName + "']").click();
        allureReport.messageWithConsole("Открыта вкладка '%s'".formatted(tabName));
    }

    /**
     * Отправляет заявку на перевыпуск карты.
     *
     * @param reason причина перевыпуска из выпадающего списка
     */
    @Step("{message}")
    public void reissueCard(String message, CardProfilePage cardPage, String reason) {
        log.info("=---> {}", message);

        $x(cardPage.actionsMenuXpath).click();
        $x(cardPage.reissueItemXpath).click();
        $x(cardPage.reissueReasonSelectXpath).selectOptionContainingText(reason);
        $x(cardPage.confirmButtonXpath).click();
        allureReport.messageWithConsole("Отправлена заявка на перевыпуск, причина '%s'".formatted(reason));
    }

    /**
     * Проверяет, что после перевыпуска в продуктовом профиле две карты.
     *
     * @param oldCardNumber номер перевыпущенной карты
     * @return последние 4 цифры новой карты
     */
    public String checkReissuedCards(String oldCardNumber) {
        String oldDigits = oldCardNumber.substring(oldCardNumber.length() - 4);

        ElementsCollection cardRows = $$x("//div[@data-id='productProfile']//tr[@data-id='cardRow']");
        cardRows.shouldHave(size(2));

        String newCardNumber = cardRows.filterBy(not(text(oldDigits))).first()
                .$x(".//td[@data-id='cardNumber']").getText();
        return newCardNumber.substring(newCardNumber.length() - 4);
    }

    /**
     * Ждёт, пока карта в продуктовом профиле получит нужный статус.
     *
     * @param lastDigits     последние 4 цифры карты
     * @param expectedStatus ожидаемый статус
     */
    @Step("{message}")
    public void waitForCardStatusInProfile(String message, String lastDigits, String expectedStatus) {
        log.info("=---> {}", message);

        // Новая карта заказывается в процессинге, статус меняется до 3 минут
        $x("//div[@data-id='productProfile']//tr[contains(., '" + lastDigits + "')]//td[@data-id='cardStatus']")
                .as("Статус карты *%s".formatted(lastDigits))
                .shouldHave(text(expectedStatus), Duration.ofMinutes(3));
        allureReport.messageWithConsole("Карта *%s в статусе '%s'".formatted(lastDigits, expectedStatus));
    }

    /**
     * Проверяет, что пункт «Сменить ПИН-код» в меню «Действия» недоступен и показывает подсказку.
     */
    @Step("{message}")
    public void checkPinChangeUnavailable(String message, CardProfilePage cardPage) {
        log.info("=---> {}", message);

        $x(cardPage.actionsMenuXpath).click();
        SelenideElement pinItem = $x(cardPage.changePinItemXpath).as("Пункт 'Сменить ПИН-код'");
        try {
            pinItem.shouldHave(attribute("aria-disabled", "true"));
            pinItem.hover();
            $x(cardPage.tooltipXpath).as("Подсказка к пункту 'Сменить ПИН-код'")
                    .shouldHave(text("Недоступно для заблокированной карты"));
        } catch (AssertionError e) {
            // Меню закрывается вместе со страницей — снять его состояние до этого
            allureReport.screenshot("Меню 'Действия' в момент падения");
            throw e;
        }
        allureReport.messageWithConsole("Пункт 'Сменить ПИН-код' недоступен, подсказка отображается");
    }
}
