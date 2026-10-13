package CFT.PRODUCT.R2_DEPOSIT.pages.operation_receiptByCashier;

import CFT.api.CftApi;
import io.qameta.allure.Step;
import model_cft.model.DOCUMENTS.main_docum.DtoMainDocum;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

/**
 * Приём документа кассиром.
 */
public class ReceiptDocumentByCashierPageHelper {

    private final DtoMainDocum docum;
    private final Map<String, Object> form = new HashMap<>();

    public ReceiptDocumentByCashierPageHelper(DtoMainDocum docum) {
        this.docum = docum;
    }

    @Step("Выполнить приём документа кассиром")
    public ReceiptDocumentByCashierPageHelper execute() {
        return this;
    }

    @Step("Указать сумму документа: {sum}")
    public ReceiptDocumentByCashierPageHelper setSumDoc(BigDecimal sum) {
        form.put("sum", sum.toPlainString());
        return this;
    }

    @Step("Отметить «Проводка»")
    public ReceiptDocumentByCashierPageHelper setOnCheckBoxWiring() {
        form.put("wiring", true);
        return this;
    }

    @Step("Нажать «ОК»")
    public ReceiptDocumentByCashierPageHelper clickOk() {
        CftApi.operation("documents/%d/receipt".formatted(docum.getId()), form).orFail("Приём документа кассиром");
        return this;
    }
}
