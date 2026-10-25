package tests.PRODUCTS.R2_DEPOSIT.rko_fl;

import CFT.PRODUCT.R2_DEPOSIT.pages.operation_SignContract.ContractSignPageHelper;
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
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.REFERENCES.com_status_prd.enums.ComStatusPrd;
import model_cft.model.REFERENCES.r2_fin_product.enums.R2FinProduct;
import model_cft.model.user.CriteriaUser;
import model_cft.model.user.Dto_User;
import org.testng.annotations.Test;
import tests.BasicTest;
import utils.AssertionsUtil;
import utils.Timer;

import java.time.LocalDate;
import java.util.List;
import java.util.Objects;

@Epic("РКО ФЛ")
@Feature("Текущий счет")
public class OpenCurrentAccountTest extends BasicTest {

    private DtoClPriv clPriv;
    private Dto_User user;

    @Test(groups = {"@900116", "parallel"},
            description = "Открытие договора текущего счёта в рублях")
    @TestitStatus(autoTestId = "1100116", autoTestExternalId = "@900116")
    public void tm_900116_OpenCurrentAccount() {

        setup();

        authorization(user);

        Dto_Deposit deposit = new OpenNewDepositPageHelper()
                .execute()
                .setClient(clPriv.getClient())
                .setFinProduct(R2FinProduct.$ALL_TEK_ALL_AL)
                .setCurrency(Currency.RUB)
                .goTabCharacteristicsAgreement()
                .setSeller(user)
                .returnOnMainTab()
                .clickOk()
                .getObject();

        AssertionsUtil.assertThat(deposit)
                .hasStateEqual(ComStatusPrd.$WAIT_CONF);

        new ContractSignPageHelper(deposit)
                .execute()
                .clickOk();

        AssertionsUtil.assertThat(deposit.update())
                .hasStateEqual(ComStatusPrd.$WORK)
                .whereR2AnnAccount(Timer.setDefault(), account -> account
                        .hasStatusEqualTo(ComStatusPrd.$OPEN));
    }

    @Step("Подготовка тестовых данных")
    private void setup() {

        for (Branch branch : List.of(Branch.$MOSCOW)) {  // на RTEST клиенты с FATCA только в этом филиале

            user = new CriteriaUser()
                    .withUnitEq(branch)
                    .withRoles(UserRole.$OPER_FL)
                    .findUser();

            CriteriaClPriv clPrivCriteria = new CriteriaClPriv()
                    .withBranchEqualTo(branch)
                    .withResident()
                    .withAlive()
                    .withNameNotEqualTo("Иванов Иван Иванович")
                    .withDocDateEndNotExpired(LocalDate.now())
                    .withoutBlocks()
                    .withCrs();
            clPrivCriteria.getQueryBuilder().where("cp.ID NOT IN (SELECT ep.C_CLIENT FROM Z#EXECUTORY_PROCESS ep)");  // в CriteriaClPriv такого метода нет
            clPrivCriteria.getQueryBuilder().where("""
                    EXISTS (SELECT 1
                            FROM Z#SHB_FORMA_FATCA f
                            WHERE f.C_CLIENT = cp.ID
                              AND f.C_DATE_END IS NULL
                               OR f.C_DATE_END >= DATE '%s')""".formatted(LocalDate.now()));
            clPriv = clPrivCriteria.getRandomObject(10);

            if (Objects.nonNull(user) && Objects.nonNull(clPriv)) {

                break;
            }
        }

        AssertionsUtil.assertThat(clPriv).objectExist();
    }
}
