package tests.PRODUCTS.R2_DEPOSIT.rko_fl;

import CFT.PRODUCT.R2_DEPOSIT.pages.operation_Add_Block.AddBlockPageHelper;
import enums.Branch;
import enums.UserRole;
import io.qameta.allure.Epic;
import io.qameta.allure.Feature;
import io.qameta.allure.Step;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import model_cft.model.FINTOOLS.ft_money.enums.Currency;
import model_cft.model.PRODUCTS.r2DepHold.enums.R2HoldKind;
import model_cft.model.PRODUCTS.r2_deposit.CriteriaR2Deposit;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.REFERENCES.com_status_prd.enums.ComStatusPrd;
import model_cft.model.REFERENCES.r2_fin_product.enums.R2FinProduct;
import model_cft.model.user.CriteriaUser;
import model_cft.model.user.Dto_User;
import org.assertj.core.api.Assertions;
import org.testng.annotations.Test;
import tests.BasicTest;
import utils.AssertionsUtil;

import java.math.BigDecimal;
import java.util.Objects;

@Epic("РКО ФЛ")
@Feature("Блокировки")
public class ArrestOnCurrentAccountTest extends BasicTest {

    private static final BigDecimal ARREST_SUM = new BigDecimal("5000.00");

    private final DepositDbSteps dbSteps = new DepositDbSteps();

    private Dto_Deposit deposit;
    private Dto_User user;

    /**
     * MAIN (ORACLE): RTEST, INTEST.
     */
    @Test(groups = {"@900118", "parallel"},
            description = "Наложение ареста на текущий счёт")
    @TestitStatus(autoTestId = "1100118", autoTestExternalId = "@900118")
    public void tm_900118_ArrestOnCurrentAccount() {

        body();
    }

    /**
     * RF (POSTGRES): PGRF1RT, RF2RT.
     */
    @Test(groups = {"@900218", "parallel"},
            description = "Наложение ареста на текущий счёт")
    @TestitStatus(autoTestId = "1100218", autoTestExternalId = "@900218")
    public void tm_900218_ArrestOnCurrentAccount() {

        body();
    }

    private void body() {

        setup();

        BigDecimal availableBefore = dbSteps.getAvailableBalance(deposit);

        authorization(user);

        new AddBlockPageHelper(deposit)
                .execute()
                .setHoldKind(R2HoldKind.$ARREST)
                .setSum(ARREST_SUM)
                .setReason("Постановление ФССП № 12345/26/77001-ИП")
                .clickOk();

        Assertions.assertThat(dbSteps.countHolds(deposit))
                .isPositive();

        Assertions.assertThat(dbSteps.getAvailableBalance(deposit))
                .as("Доступный остаток уменьшился на сумму ареста")
                .isEqualByComparingTo(availableBefore.subtract(ARREST_SUM));
    }

    @Step("Подготовка тестовых данных")
    private void setup() {

        for (Branch branch : getProductBranchesWithCheckOperDayEqualCurrDay()) {

            deposit = new CriteriaR2Deposit()
                    .withBranchEqualTo(branch)
                    .withStatusEqualTo(ComStatusPrd.$WORK)
                    .withCurrencyEqualTo(Currency.RUB)
                    .withFinProductEqualTo(R2FinProduct.$ALL_TEK_ALL_AL)
                    .withBalanceGreaterThanOrEqualTo(new BigDecimal("10000"))
                    .withoutActiveHold()
                    .getRandomObject(10);

            if (Objects.isNull(deposit)) {

                continue;
            }

            user = new CriteriaUser()
                    .withDepartEq(deposit.getLinkDepart())
                    .withRoles(UserRole.$OPER_FL)
                    .findUser();

            if (Objects.nonNull(user)) {

                break;
            }
        }

        AssertionsUtil.assertThat(deposit).objectExist();
        AssertionsUtil.assertThat(user).objectExist();
    }
}
