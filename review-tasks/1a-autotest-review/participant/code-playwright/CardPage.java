package ru.rshb.pw.cards;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.PlaywrightException;
import com.microsoft.playwright.options.AriaRole;
import io.qameta.allure.Step;

import java.util.regex.Pattern;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class CardPage {

    private final Page page;

    public CardPage(Page page) {
        this.page = page;
    }

    public Locator status() {
        return page.getByTestId("cardStatus");
    }

    public Locator blockReason() {
        return page.getByTestId("blockReason");
    }

    public Locator balance() {
        return page.getByTestId("cardBalance");
    }

    public Locator notification() {
        return page.getByRole(AriaRole.ALERT);
    }

    public Locator transferLimitInput() {
        return page.getByLabel("Переводы, в месяц");
    }

    @Step("Найти клиента по паспорту {series} {number} и открыть карту *{lastDigits}")
    public CardPage open(String series, String number, String lastDigits) {
        page.getByLabel("Серия паспорта").fill(series);
        page.getByLabel("Номер паспорта").fill(number);
        button("Найти").click();
        page.getByRole(AriaRole.LINK, new Page.GetByRoleOptions().setName(Pattern.compile(lastDigits + "$"))).click();
        assertThat(page.getByTestId("cardProfile")).isVisible();
        return this;
    }

    @Step("Открыть вкладку «{name}»")
    public void openTab(String name) {
        page.getByRole(AriaRole.TAB, new Page.GetByRoleOptions().setName(name)).click();
    }

    @Step("Заблокировать карту с причиной «{reason}»")
    public void block(String reason) {
        button("Заблокировать").click();
        page.getByLabel("Причина блокировки").selectOption(reason);
        button("Подтвердить").click();
    }

    @Step("Временно заблокировать карту")
    public void blockTemporarily() {
        button("Временная блокировка").click();
        button("Подтвердить").click();
    }

    @Step("Снять временную блокировку")
    public void removeTemporaryBlock() {
        button("Снять временную блокировку").click();
        button("Подтвердить").click();
    }

    @Step("Установить лимит на переводы {amount}")
    public void setTransferLimit(String amount) {
        openTab("Лимиты");
        transferLimitInput().fill(amount);
        button("Сохранить").click();
    }

    public boolean isCardNumberMasked() {
        try {
            Locator cardNumber = page.getByTestId("requisites").getByTestId("cardNumber");
            cardNumber.waitFor(new Locator.WaitForOptions().setTimeout(5000));
            return cardNumber.textContent().startsWith("•••• ");
        } catch (PlaywrightException e) {
            return false;
        }
    }

    private Locator button(String name) {
        return page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName(name).setExact(true));
    }
}
