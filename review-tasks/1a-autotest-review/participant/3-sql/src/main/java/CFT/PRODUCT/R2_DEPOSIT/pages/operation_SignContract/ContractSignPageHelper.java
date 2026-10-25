package CFT.PRODUCT.R2_DEPOSIT.pages.operation_SignContract;

import CFT.api.CftApi;
import io.qameta.allure.Step;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;

import java.util.Map;

/**
 * Операция «Подписать договор».
 */
public class ContractSignPageHelper {

    private final Dto_Deposit deposit;

    public ContractSignPageHelper(Dto_Deposit deposit) {
        this.deposit = deposit;
    }

    @Step("Выполнить операцию «Подписать договор»")
    public ContractSignPageHelper execute() {
        return this;
    }

    @Step("Нажать «ОК»")
    public ContractSignPageHelper clickOk() {
        CftApi.operation("deposits/%d/sign".formatted(deposit.getId()), Map.of()).orFail("Подписать договор");
        return this;
    }
}
