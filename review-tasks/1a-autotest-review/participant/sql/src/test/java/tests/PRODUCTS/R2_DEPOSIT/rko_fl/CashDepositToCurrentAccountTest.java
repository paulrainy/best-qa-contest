package tests.PRODUCTS.R2_DEPOSIT.rko_fl;

import CFT.PRODUCT.R2_DEPOSIT.pages.operation_incomingCash.IncomingCashPageHelper;
import CFT.PRODUCT.R2_DEPOSIT.pages.operation_receiptByCashier.ReceiptDocumentByCashierPageHelper;
import enums.Branch;
import enums.CashboxSymbol;
import enums.StatesFactOper;
import enums.StatesMainDocum;
import enums.UserRole;
import io.qameta.allure.Epic;
import io.qameta.allure.Feature;
import io.qameta.allure.Step;
import main.java.ru.rshb.testitwork.annotations.TestitStatus;
import model_cft.model.CLIENTS.clPriv.CriteriaClPriv;
import model_cft.model.FINTOOLS.ft_money.enums.Currency;
import model_cft.model.PRODUCTS.fact_oper.entities.DtoR2FactOper;
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

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

@Epic("РКО ФЛ")
@Feature("Текущий счет")
public class CashDepositToCurrentAccountTest extends BasicTest {

    private static final BigDecimal AMOUNT = new BigDecimal("1500.00");

    private final DepositDbSteps dbSteps = new DepositDbSteps();

    private Dto_Deposit deposit;
    private Dto_User operFl;
    private Dto_User cashier;

    @Test(groups = {"@900117", "parallel"},
            description = "Взнос наличных на текущий счёт")
    @TestitStatus(autoTestId = "1100117", autoTestExternalId = "@900117")
    public void tm_900117_CashDepositToCurrentAccount() {

        setup();

        BigDecimal balanceBefore = deposit.getBalance();

        authorization(operFl);

        new IncomingCashPageHelper(deposit)
                .execute()
                .setAmountToBeCredited(AMOUNT)
                .setCashBoxSymbols(CashboxSymbol.RECEIPTS_TO_CL_PRIV_DEPOSIT_ACCOUNT)
                .clickOk();

        // Хелпер не возвращает созданную ФО — берём последнюю по договору из БД
        DtoR2FactOper factOper = dbSteps.getLastFactOper(deposit);

        AssertionsUtil.assertThat(factOper)
                .objectExist()
                .hasStateEqual(StatesFactOper.$ADDITIONAL_CONTROL)
                .whereMainDocum(doc -> doc
                        .hasStateEqual(StatesMainDocum.$TO_KASSA));

        authorization(cashier);

        new ReceiptDocumentByCashierPageHelper(factOper.getMainDocum())
                .execute()
                .setSumDoc(AMOUNT)
                .setOnCheckBoxWiring()
                .clickOk();

        // Проводку выполняет фоновое задание, на стендах RF — до 10 минут
        AssertionsUtil.assertThat(factOper.update())
                .hasStateEqual(StatesFactOper.$PERFORMED, Timer.set(10, 600, TimeUnit.SECONDS))
                .whereMainDocum(doc -> doc
                        .hasStateEqual(StatesMainDocum.$PROV));

        AssertionsUtil.assertThat(deposit.update())
                .hasBalanceEqualTo(balanceBefore.add(AMOUNT));
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
                    .joinClPriv(new CriteriaClPriv()
                            .withResident()
                            .withAlive()
                            .withDocDateEndNotExpired(LocalDate.now())
                            .withoutBlocks())
                    .getRandomObject(10);

            if (Objects.isNull(deposit)) {

                continue;
            }

            operFl = new CriteriaUser()
                    .withDepartEq(deposit.getLinkDepart())
                    .withRoles(UserRole.$OPER_FL)
                    .findUser();

            cashier = new CriteriaUser()
                    .withDepartEq(deposit.getLinkDepart())
                    .withRoles(UserRole.$CASHIER)
                    .findUser();

            if (Objects.nonNull(operFl) && Objects.nonNull(cashier)) {

                break;
            }
        }

        AssertionsUtil.assertThat(deposit).objectExist();
        AssertionsUtil.assertThat(operFl).objectExist();
        AssertionsUtil.assertThat(cashier).objectExist();
    }
}
