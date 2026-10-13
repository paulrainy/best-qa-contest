package utils.asserts;

import io.qameta.allure.Allure;
import model_cft.model.ACCOUNTS.ac_fin.DtoAcFin;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.REFERENCES.com_status_prd.enums.ComStatusPrd;
import utils.Timer;

/**
 * Проверки счёта договора.
 */
public class AccountAssert {

    private final Dto_Deposit deposit;
    private final Timer timer;

    AccountAssert(Dto_Deposit deposit, Timer timer) {
        this.deposit = deposit;
        this.timer = timer;
    }

    public AccountAssert hasStatusEqualTo(ComStatusPrd status) {
        Allure.step("Проверить: счёт договора в состоянии «%s»".formatted(status.getDescription()), () -> {
            if (!timer.waitFor(() -> status.getCode().equals(deposit.getAccount().getStatusCode()))) {
                DtoAcFin account = deposit.getAccount();
                throw new AssertionError("Счёт %s договора %s: ожидалось состояние %s, фактически %s (ждали %d с)"
                        .formatted(account.getNumber(), deposit, status.getCode(), account.getStatusCode(),
                                timer.getTimeoutSeconds()));
            }
        });
        return this;
    }
}
