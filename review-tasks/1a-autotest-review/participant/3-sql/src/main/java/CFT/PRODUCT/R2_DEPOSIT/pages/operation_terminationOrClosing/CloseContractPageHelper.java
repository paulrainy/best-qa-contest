package CFT.PRODUCT.R2_DEPOSIT.pages.operation_terminationOrClosing;

import CFT.api.CftApi;
import io.qameta.allure.Step;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;

import java.util.Map;

/**
 * Операция «Закрыть договор».
 */
public class CloseContractPageHelper {

    private final Dto_Deposit deposit;

    public CloseContractPageHelper(Dto_Deposit deposit) {
        this.deposit = deposit;
    }

    @Step("Выполнить операцию «Закрыть договор»")
    public CloseContractPageHelper execute() {
        return this;
    }

    @Step("Нажать «ОК»")
    public CloseContractPageHelper clickOk() {
        CftApi.operation("deposits/%d/close".formatted(deposit.getId()), Map.of()).orFail("Закрыть договор");
        return this;
    }
}
