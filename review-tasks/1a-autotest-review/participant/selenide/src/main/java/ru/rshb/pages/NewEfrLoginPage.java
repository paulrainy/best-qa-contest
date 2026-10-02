package ru.rshb.pages;

import ru.rshb.entities.WebUser;

import java.time.Duration;

import static com.codeborne.selenide.Condition.visible;
import static com.codeborne.selenide.Selenide.$x;

public class NewEfrLoginPage {

    public void login(WebUser webUser) {
        $x("//input[@name='login']").setValue(webUser.getLogin());
        $x("//input[@name='password']").setValue(webUser.getPassword());
        $x("//button[normalize-space()='Войти']").click();
        $x("//form[@data-id='clientSearch']").shouldBe(visible, Duration.ofSeconds(15));
    }
}
