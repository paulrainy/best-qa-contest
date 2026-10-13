package utils.asserts;

import enums.StatesMainDocum;
import io.qameta.allure.Allure;
import model_cft.model.DOCUMENTS.main_docum.DtoMainDocum;
import utils.Timer;

/**
 * Проверки документа операции.
 */
public class MainDocumAssert {

    private final DtoMainDocum docum;

    MainDocumAssert(DtoMainDocum docum) {
        this.docum = docum;
    }

    public MainDocumAssert hasStateEqual(StatesMainDocum state) {
        Timer timer = Timer.setDefault();
        Allure.step("Проверить: %s в состоянии «%s»".formatted(docum, state.getDescription()), () -> {
            if (!timer.waitFor(() -> state.getCode().equals(docum.update().getState()))) {
                throw new AssertionError("%s: ожидалось состояние %s, фактически %s (ждали %d с)".formatted(
                        docum, state.getCode(), docum.getState(), timer.getTimeoutSeconds()));
            }
        });
        return this;
    }
}
