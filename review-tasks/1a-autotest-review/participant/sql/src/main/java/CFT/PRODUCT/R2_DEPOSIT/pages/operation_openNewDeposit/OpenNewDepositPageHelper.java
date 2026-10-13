package CFT.PRODUCT.R2_DEPOSIT.pages.operation_openNewDeposit;

import CFT.api.CftApi;
import io.qameta.allure.Step;
import model_cft.model.CLIENTS.client.DtoClient;
import model_cft.model.DaoCommon;
import model_cft.model.FINTOOLS.ft_money.enums.Currency;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.REFERENCES.r2_fin_product.enums.R2FinProduct;
import model_cft.model.user.Dto_User;

import java.util.HashMap;
import java.util.Map;

/**
 * Операция «Открыть новый договор».
 */
public class OpenNewDepositPageHelper {

    private static final String OPERATION = "Открыть новый договор";

    private final Map<String, Object> form = new HashMap<>();
    private Long depositId;
    private String error;

    @Step("Выполнить операцию «Открыть новый договор»")
    public OpenNewDepositPageHelper execute() {
        return this;
    }

    @Step("Указать клиента: {client}")
    public OpenNewDepositPageHelper setClient(DtoClient client) {
        form.put("clientId", client.getId());
        return this;
    }

    @Step("Указать финансовый продукт: {finProduct}")
    public OpenNewDepositPageHelper setFinProduct(R2FinProduct finProduct) {
        form.put("finProduct", finProduct.getCode());
        return this;
    }

    @Step("Указать валюту: {currency}")
    public OpenNewDepositPageHelper setCurrency(Currency currency) {
        form.put("currency", currency.getCode());
        return this;
    }

    @Step("Перейти на вкладку «Характеристики договора»")
    public OpenNewDepositPageHelper goTabCharacteristicsAgreement() {
        return this;
    }

    @Step("Указать продавца: {seller}")
    public OpenNewDepositPageHelper setSeller(Dto_User seller) {
        form.put("sellerId", seller.getId());
        return this;
    }

    @Step("Вернуться на основную вкладку")
    public OpenNewDepositPageHelper returnOnMainTab() {
        return this;
    }

    /**
     * Нажать «ОК». Падает, если ЦФТ вернул ошибку.
     */
    @Step("Нажать «ОК»")
    public OpenNewDepositPageHelper clickOk() {
        depositId = CftApi.operation("deposits", form).orFail(OPERATION).body().get("id").asLong();
        return this;
    }

    /**
     * Нажать «ОК» в негативном тесте: ошибку не проверяет, её текст доступен в checkErrorTextEqualTo.
     */
    @Step("Нажать «ОК» (ожидается ошибка: {expectError})")
    public OpenNewDepositPageHelper clickOk(boolean expectError) {
        if (!expectError) {
            return clickOk();
        }
        CftApi.Result result = CftApi.operation("deposits", form);
        error = result.error();
        if (error == null) {
            depositId = result.body().get("id").asLong();
        }
        return this;
    }

    @Step("Проверить текст ошибки: «{expected}»")
    public OpenNewDepositPageHelper checkErrorTextEqualTo(String expected) {
        if (error == null) {
            throw new AssertionError("ЦФТ не вернул ошибку, договор создан (ID %d)".formatted(depositId));
        }
        if (!expected.equals(error)) {
            throw new AssertionError("Текст ошибки: ожидался «%s», фактически «%s»".formatted(expected, error));
        }
        return this;
    }

    /**
     * Созданный договор из БД.
     */
    public Dto_Deposit getObject() {
        if (depositId == null) {
            throw new IllegalStateException("Договор не создан");
        }
        return DaoCommon.getInstance().selectOne("SELECT * FROM Z#R2_DEPOSIT WHERE ID = :id", Dto_Deposit.class,
                Map.of("id", depositId));
    }
}
