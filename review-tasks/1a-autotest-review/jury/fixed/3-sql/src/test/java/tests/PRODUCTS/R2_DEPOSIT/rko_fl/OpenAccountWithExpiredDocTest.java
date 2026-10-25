package tests.PRODUCTS.R2_DEPOSIT.rko_fl;

import CFT.PRODUCT.R2_DEPOSIT.pages.operation_openNewDeposit.OpenNewDepositPageHelper;
import enums.Branch;
import enums.UserRole;
import io.qameta.allure.Epic;
import io.qameta.allure.Feature;
import io.qameta.allure.Step;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import model_cft.model.CLIENTS.clPriv.CriteriaClPriv;
import model_cft.model.CLIENTS.clPriv.DtoClPriv;
import model_cft.model.FINTOOLS.ft_money.enums.Currency;
import model_cft.model.PRODUCTS.r2_deposit.CriteriaR2Deposit;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.REFERENCES.r2_fin_product.enums.R2FinProduct;
import model_cft.model.user.CriteriaUser;
import model_cft.model.user.Dto_User;
import org.testng.annotations.Test;
import tests.BasicTest;
import utils.AssertionsUtil;

import java.time.LocalDate;
import java.util.Objects;

@Epic("РКО ФЛ")
@Feature("Текущий счет")
public class OpenAccountWithExpiredDocTest extends BasicTest {

    private DtoClPriv clPriv;
    private Dto_User user;

    @Test(groups = {"@900120", "parallel"},
            description = "Отказ в открытии текущего счёта клиенту с истёкшим ДУЛ")
    @TestitStatus(autoTestId = "1100120", autoTestExternalId = "@900120")
    public void tm_900120_OpenAccountWithExpiredDoc() {

        setup();

        authorization(user);

        new OpenNewDepositPageHelper()
                .execute()
                .setClient(clPriv.getClient())
                .setFinProduct(R2FinProduct.$ALL_TEK_ALL_AL)
                .setCurrency(Currency.RUB)
                .goTabCharacteristicsAgreement()
                .setSeller(user)
                .returnOnMainTab()
                .clickOk(true)
                .checkErrorTextEqualTo("Срок действия документа, удостоверяющего личность, истёк");

        Dto_Deposit deposit = new CriteriaR2Deposit()
                .withClientEqualTo(clPriv)
                .withCreateDateEqualTo(getOperDay())
                .getObject();

        AssertionsUtil.assertThat(deposit).objectNotExist();
    }

    @Step("Подготовка тестовых данных")
    private void setup() {

        for (Branch branch : getProductBranchesWithCheckOperDayEqualCurrDay()) {

            clPriv = new CriteriaClPriv()
                    .withBranchEqualTo(branch)
                    .withResident()
                    .withAlive()
                    .withDocDateEndExpired(LocalDate.now())
                    .withoutBlocks()
                    .getRandomObject(10);

            if (Objects.isNull(clPriv)) {

                continue;
            }

            user = new CriteriaUser()
                    .withUnitEq(branch)
                    .withRoles(UserRole.$OPER_FL)
                    .findUser();

            if (Objects.nonNull(user)) {

                break;
            }
        }

        AssertionsUtil.assertThat(clPriv).objectExist();
        AssertionsUtil.assertThat(user).objectExist();
    }
}
