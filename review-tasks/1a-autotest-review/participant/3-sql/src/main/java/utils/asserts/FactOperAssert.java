package utils.asserts;

import enums.StatesFactOper;
import io.qameta.allure.Allure;
import model_cft.model.PRODUCTS.fact_oper.entities.DtoR2FactOper;
import utils.Timer;

import java.util.function.Consumer;

/**
 * Проверки фактической операции. Состояние перечитывается из БД, пока не станет ожидаемым.
 */
public class FactOperAssert extends CftObjectAssert<FactOperAssert, DtoR2FactOper> {

    public FactOperAssert(DtoR2FactOper actual) {
        super(actual, "Фактическая операция");
    }

    public FactOperAssert hasStateEqual(StatesFactOper state) {
        return hasStateEqual(state, Timer.setDefault());
    }

    public FactOperAssert hasStateEqual(StatesFactOper state, Timer timer) {
        DtoR2FactOper factOper = requireActual();
        Allure.step("Проверить: %s в состоянии «%s»".formatted(factOper, state.getDescription()), () -> {
            if (!timer.waitFor(() -> state.getCode().equals(factOper.update().getState()))) {
                throw new AssertionError("%s: ожидалось состояние %s, фактически %s (ждали %d с)".formatted(
                        factOper, state.getCode(), factOper.getState(), timer.getTimeoutSeconds()));
            }
        });
        return this;
    }

    public FactOperAssert whereMainDocum(Consumer<MainDocumAssert> checks) {
        checks.accept(new MainDocumAssert(requireActual().getMainDocum()));
        return this;
    }
}
