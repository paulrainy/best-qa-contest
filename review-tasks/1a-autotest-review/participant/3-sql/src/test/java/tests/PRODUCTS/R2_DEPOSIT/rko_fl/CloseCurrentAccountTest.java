package tests.PRODUCTS.R2_DEPOSIT.rko_fl;

import CFT.PRODUCT.R2_DEPOSIT.pages.operation_terminationOrClosing.CloseContractPageHelper;
import enums.Branch;
import enums.UserRole;
import io.qameta.allure.Epic;
import io.qameta.allure.Feature;
import io.qameta.allure.Step;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import model_cft.model.DaoCommon;
import model_cft.model.FINTOOLS.ft_money.enums.Currency;
import model_cft.model.PRODUCTS.r2_deposit.CriteriaR2Deposit;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.REFERENCES.com_status_prd.enums.ComStatusPrd;
import model_cft.model.REFERENCES.r2_fin_product.enums.R2FinProduct;
import model_cft.model.user.CriteriaUser;
import model_cft.model.user.Dto_User;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.testng.annotations.Test;
import tests.BasicTest;
import utils.AssertionsUtil;

import java.util.Map;
import java.util.Objects;

@Epic("РКО ФЛ")
@Feature("Текущий счет")
public class CloseCurrentAccountTest extends BasicTest {

    private static final Logger log = LogManager.getLogger(CloseCurrentAccountTest.class);

    private Dto_Deposit deposit;
    private Dto_User user;

    @Test(groups = {"@900119", "parallel"},
            description = "Закрытие текущего счёта с нулевым остатком")
    @TestitStatus(autoTestId = "1100119", autoTestExternalId = "@900119")
    public void tm_900119_CloseCurrentAccount() {

        setup();

        // Договоров с нулевым остатком на стенде мало — обнуляем остаток сами
        setZeroBalance(deposit);

        authorization(user);

        try {
            new CloseContractPageHelper(deposit).execute().clickOk();
        } catch (AssertionError e) {
            log.error("Закрытие не прошло", e);
        }

        AssertionsUtil.assertThat(deposit.update())
                .hasStateEqual(ComStatusPrd.$CLOSE)
                .hasDateCloseEqualTo(deposit.getDateClose());
    }

    @Step("Подготовка тестовых данных")
    private void setup() {

        for (Branch branch : getProductBranchesWithCheckOperDayEqualCurrDay()) {

            CriteriaR2Deposit depositCriteria = new CriteriaR2Deposit()
                    .withBranchEqualTo(branch)
                    .withStatusEqualTo(ComStatusPrd.$WORK)
                    .withCurrencyEqualTo(Currency.RUB)
                    .withFinProductEqualTo(R2FinProduct.$ALL_TEK_ALL_AL)
                    .withoutActiveHold();
            depositCriteria.getQueryBuilder()  // без действующих карт
                    .join("LEFT JOIN Z#R2_IP_CARDS ic ON ic.C_DEPOSIT = d.ID")
                    .where("ic.C_STATE <> 'ACTIVE'");
            deposit = depositCriteria.getRandomObject(10);

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

    @Step("Обнулить остаток на счёте договора {deposit.numDog}")
    private void setZeroBalance(Dto_Deposit deposit) {

        String sql = """
                UPDATE Z#AC_FIN
                SET C_SALDO = 0
                WHERE ID = :accountId""";

        DaoCommon.getInstance().executeUpdate(sql, Map.of("accountId", deposit.getAccountId()));
    }
}
