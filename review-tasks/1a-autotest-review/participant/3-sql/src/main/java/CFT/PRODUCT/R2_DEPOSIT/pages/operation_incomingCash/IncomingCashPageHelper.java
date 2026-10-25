package CFT.PRODUCT.R2_DEPOSIT.pages.operation_incomingCash;

import CFT.api.CftApi;
import enums.CashboxSymbol;
import io.qameta.allure.Step;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

/**
 * Операция «Приходная кассовая операция».
 */
public class IncomingCashPageHelper {

    private final Dto_Deposit deposit;
    private final Map<String, Object> form = new HashMap<>();

    public IncomingCashPageHelper(Dto_Deposit deposit) {
        this.deposit = deposit;
    }

    @Step("Выполнить операцию «Приходная кассовая операция»")
    public IncomingCashPageHelper execute() {
        return this;
    }

    @Step("Указать сумму к зачислению: {amount}")
    public IncomingCashPageHelper setAmountToBeCredited(BigDecimal amount) {
        form.put("amount", amount.toPlainString());
        return this;
    }

    @Step("Указать символ кассы: {symbol}")
    public IncomingCashPageHelper setCashBoxSymbols(CashboxSymbol symbol) {
        form.put("cashSymbol", symbol.getCode());
        return this;
    }

    @Step("Нажать «ОК»")
    public IncomingCashPageHelper clickOk() {
        CftApi.operation("deposits/%d/incoming-cash".formatted(deposit.getId()), form)
                .orFail("Приходная кассовая операция");
        return this;
    }
}
