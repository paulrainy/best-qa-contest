package tests.PRODUCTS.R2_DEPOSIT.rko_fl;

import CFT.PRODUCT.R2_DEPOSIT.pages.operation_terminationOrClosing.CloseContractPageHelper;
import enums.Branch;
import enums.UserRole;
import io.qameta.allure.Epic;
import io.qameta.allure.Feature;
import io.qameta.allure.Step;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import model_cft.model.FINTOOLS.ft_money.enums.Currency;
import model_cft.model.PRODUCTS.r2_deposit.CriteriaR2Deposit;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.REFERENCES.com_status_prd.enums.ComStatusPrd;
import model_cft.model.REFERENCES.r2_fin_product.enums.R2FinProduct;
import model_cft.model.user.CriteriaUser;
import model_cft.model.user.Dto_User;
import org.testng.annotations.Test;
import tests.BasicTest;
import utils.AssertionsUtil;
import utils.Timer;

import java.util.Objects;

@Epic("РКО ФЛ")
@Feature("Текущий счет")
public class CloseCurrentAccountTest extends BasicTest {

    private final DepositDbSteps dbSteps = new DepositDbSteps();

    private Dto_Deposit deposit;
    private Dto_User user;

    @Test(groups = {"@900119", "parallel"},
            description = "Закрытие текущего счёта с нулевым остатком")
    @TestitStatus(autoTestId = "1100119", autoTestExternalId = "@900119")
    public void tm_900119_CloseCurrentAccount() {

        setup();

        // Договоров с нулевым остатком на стенде мало — обнуляем остаток сами
        dbSteps.setZeroBalance(deposit);

        authorization(user);

        new CloseContractPageHelper(deposit)
                .execute()
                .clickOk();

        AssertionsUtil.assertThat(deposit.update())
                .hasStateEqual(ComStatusPrd.$CLOSE)
                .hasDateCloseEqualTo(getOperDay())
                .whereR2AnnAccount(Timer.setDefault(), account -> account
                        .hasStatusEqualTo(ComStatusPrd.$CLOSE));
    }

    @Step("Подготовка тестовых данных")
    private void setup() {

        for (Branch branch : getProductBranchesWithCheckOperDayEqualCurrDay()) {

            deposit = new CriteriaR2Deposit()
                    .withBranchEqualTo(branch)
                    .withStatusEqualTo(ComStatusPrd.$WORK)
                    .withCurrencyEqualTo(Currency.RUB)
                    .withFinProductEqualTo(R2FinProduct.$ALL_TEK_ALL_AL)
                    .withoutActiveHold()
                    .withoutActiveCard()
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
