package ru.rshb.pages;

import static com.codeborne.selenide.Selenide.$x;

public class NewEfrClientSearchPage {

    public void passportSeriesAndNumberInput(String series, String number) {
        $x("//input[@name='passportSeries']").setValue(series);
        $x("//input[@name='passportNumber']").setValue(number);
    }

    public void clickSearchButton() {
        $x("//form[@data-id='clientSearch']//button[normalize-space()='Найти']").click();
    }
}
