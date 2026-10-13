package utils.asserts;

import io.qameta.allure.Allure;
import model_cft.model.CHARTS_OF_ACCOUNTS.pl_usv.enums.BalanceAccount;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.REFERENCES.com_status_prd.enums.ComStatusPrd;
import utils.Timer;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.function.Consumer;

/**
 * Проверки договора. Состояние перечитывается из БД, пока не станет ожидаемым.
 */
public class DepositAssert extends CftObjectAssert<DepositAssert, Dto_Deposit> {

    public DepositAssert(Dto_Deposit actual) {
        super(actual, "Договор");
    }

    public DepositAssert hasStateEqual(ComStatusPrd status) {
        return hasStateEqual(status, Timer.setDefault());
    }

    public DepositAssert hasStateEqual(ComStatusPrd status, Timer timer) {
        Dto_Deposit deposit = requireActual();
        Allure.step("Проверить: %s в состоянии «%s»".formatted(deposit, status.getDescription()), () -> {
            if (!timer.waitFor(() -> status.getCode().equals(deposit.update().getStatusCode()))) {
                throw new AssertionError("%s: ожидалось состояние %s, фактически %s (ждали %d с)".formatted(
                        deposit, status.getCode(), deposit.getStatusCode(), timer.getTimeoutSeconds()));
            }
        });
        return this;
    }

    public DepositAssert whereR2AnnAccount(Timer timer, Consumer<AccountAssert> checks) {
        checks.accept(new AccountAssert(requireActual(), timer));
        return this;
    }

    public DepositAssert hasAccountStartWith(BalanceAccount balanceAccount) {
        Dto_Deposit deposit = requireActual();
        Allure.step("Проверить: номер счёта договора начинается с " + balanceAccount.getCode(), () -> {
            String number = deposit.getAccount().getNumber();
            if (number == null || !number.startsWith(balanceAccount.getCode())) {
                throw new AssertionError("Счёт договора %s: номер %s не начинается с %s".formatted(
                        deposit, number, balanceAccount.getCode()));
            }
        });
        return this;
    }

    public DepositAssert hasBalanceEqualTo(BigDecimal expected) {
        Dto_Deposit deposit = requireActual();
        Allure.step("Проверить: остаток по договору — " + expected, () -> {
            BigDecimal balance = deposit.getBalance();
            if (balance == null || balance.compareTo(expected) != 0) {
                throw new AssertionError("%s: ожидался остаток %s, фактически %s".formatted(deposit, expected, balance));
            }
        });
        return this;
    }

    public DepositAssert hasDateCloseEqualTo(LocalDate expected) {
        Dto_Deposit deposit = requireActual();
        Allure.step("Проверить: дата закрытия договора — " + expected, () -> {
            LocalDate dateClose = deposit.update().getDateClose();
            if (!expected.equals(dateClose)) {
                throw new AssertionError("%s: ожидалась дата закрытия %s, фактически %s".formatted(
                        deposit, expected, dateClose));
            }
        });
        return this;
    }
}
