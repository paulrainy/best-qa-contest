package ru.rshb.utils;

import com.codeborne.selenide.Selenide;
import io.qameta.allure.Allure;
import lombok.extern.log4j.Log4j2;
import org.openqa.selenium.OutputType;

import java.io.ByteArrayInputStream;

@Log4j2
public class AllureReport {

    /**
     * Заменяет имя теста в отчёте Allure.
     */
    public void replaceTestMethodName(String name) {
        Allure.getLifecycle().updateTestCase(testResult -> testResult.setName(name));
    }

    /**
     * Пишет сообщение в консоль и шагом в отчёт Allure.
     */
    public void messageWithConsole(String message) {
        log.info(message);
        Allure.step(message);
    }

    /**
     * Прикладывает к отчёту скриншот текущей страницы.
     */
    public void screenshot(String name) {
        byte[] png = Selenide.screenshot(OutputType.BYTES);
        if (png != null) {
            Allure.addAttachment(name, "image/png", new ByteArrayInputStream(png), "png");
        }
    }
}
