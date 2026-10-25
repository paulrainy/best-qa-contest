package CFT.PRODUCT.R2_DEPOSIT.pages.operation_Add_Block;

import CFT.api.CftApi;
import io.qameta.allure.Step;
import model_cft.model.PRODUCTS.r2DepHold.enums.R2HoldKind;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

/**
 * Операция «Добавить блокировку».
 */
public class AddBlockPageHelper {

    private final Dto_Deposit deposit;
    private final Map<String, Object> form = new HashMap<>();

    public AddBlockPageHelper(Dto_Deposit deposit) {
        this.deposit = deposit;
    }

    @Step("Выполнить операцию «Добавить блокировку»")
    public AddBlockPageHelper execute() {
        return this;
    }

    @Step("Указать вид блокировки: {kind}")
    public AddBlockPageHelper setHoldKind(R2HoldKind kind) {
        form.put("kind", kind.getCode());
        return this;
    }

    @Step("Указать сумму: {sum}")
    public AddBlockPageHelper setSum(BigDecimal sum) {
        form.put("sum", sum.toPlainString());
        return this;
    }

    @Step("Указать основание: {reason}")
    public AddBlockPageHelper setReason(String reason) {
        form.put("reason", reason);
        return this;
    }

    @Step("Нажать «ОК»")
    public AddBlockPageHelper clickOk() {
        CftApi.operation("deposits/%d/holds".formatted(deposit.getId()), form).orFail("Добавить блокировку");
        return this;
    }
}
