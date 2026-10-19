package tests.PRODUCTS.R2_DEPOSIT.rko_fl;

import CFT.PRODUCT.R2_DEPOSIT.pages.operation_Add_Block.AddBlockPageHelper;
import enums.Branch;
import enums.UserRole;
import io.qameta.allure.Epic;
import io.qameta.allure.Feature;
import io.qameta.allure.Step;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import model_cft.model.DaoCommon;
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
import java.util.Map;
import java.util.Objects;

@Epic("РКО ФЛ")
@Feature("Блокировки")
public class ArrestOnCurrentAccountTest extends BasicTest {

    private static final BigDecimal ARREST_SUM = new BigDecimal("5000.00");

    private Dto_Deposit deposit;
    private Dto_User user;

    /**
     * Стенды: RTEST, INTEST (Oracle), PGRF1RT (PostgreSQL).
     */
    @Test(groups = {"@900118", "parallel"},
            description = "Наложение ареста на текущий счёт")
    @TestitStatus(autoTestId = "1100118", autoTestExternalId = "@900118")
    public void tm_900118_ArrestOnCurrentAccount() {

        setup();

        BigDecimal availableBefore = getAvailableBalance(deposit);

        authorization(user);

        new AddBlockPageHelper(deposit)
                .execute()
                .setHoldKind(R2HoldKind.$ARREST)
                .setSum(ARREST_SUM)
                .setReason("Постановление ФССП № 12345/26/77001-ИП")
                .clickOk();

        Assertions.assertThat(countArrests(deposit))
                .as("Арест на 5 000,00 в состоянии «Действует» за операционный день")
                .isEqualTo(1);

        Assertions.assertThat(getAvailableBalance(deposit))
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

    @Step("Найти арест, наложенный тестом, по договору {deposit.numDog}")
    private long countArrests(Dto_Deposit deposit) {

        String sql = """
                SELECT COUNT(*)
                FROM Z#R2_DEP_HOLD h
                WHERE h.C_DEPOSIT = :depositId
                  AND h.C_KIND = :kind
                  AND h.C_SUM = :sum
                  AND h.C_STATE = 'ACTIVE'
                  AND h.C_DATE_BEGIN = :operDay""";

        return DaoCommon.getInstance().selectValue(sql, Long.class, Map.of("depositId", deposit.getId(),
                "kind", R2HoldKind.$ARREST.getCode(), "sum", ARREST_SUM, "operDay", getOperDay()));
    }

    @Step("Получить доступный остаток по договору {deposit.numDog}")
    private BigDecimal getAvailableBalance(Dto_Deposit deposit) {

        String sql = """
                SELECT a.C_SALDO - COALESCE(SUM(h.C_SUM), 0)
                FROM Z#R2_DEPOSIT d
                INNER JOIN Z#AC_FIN a ON a.ID = d.C_ACCOUNT
                LEFT JOIN Z#R2_DEP_HOLD h ON h.C_DEPOSIT = d.ID
                                         AND h.C_STATE = 'ACTIVE'
                                         AND h.C_DATE_BEGIN <= CURRENT_DATE
                WHERE d.ID = :depositId
                GROUP BY a.C_SALDO""";

        return DaoCommon.getInstance().selectValue(sql, BigDecimal.class, Map.of("depositId", deposit.getId()));
    }
}
