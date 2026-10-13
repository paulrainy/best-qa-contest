package tests.PRODUCTS.R2_DEPOSIT.rko_fl;

import io.qameta.allure.Step;
import model_cft.model.DaoCommon;
import model_cft.model.PRODUCTS.fact_oper.entities.DtoR2FactOper;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Запросы к БД по договорам РКО ФЛ, которых нет в Criteria-классах.
 */
public class DepositDbSteps {

    private final DaoCommon dao = DaoCommon.getInstance();

    @Step("Получить последнюю фактическую операцию по договору {deposit.numDog}")
    public DtoR2FactOper getLastFactOper(Dto_Deposit deposit) {

        String sql = """
                SELECT fo.*
                FROM Z#R2_FACT_OPER fo
                WHERE fo.C_DEPOSIT = :depositId
                FETCH FIRST 1 ROWS ONLY""";

        return dao.selectOne(sql, DtoR2FactOper.class, Map.of("depositId", deposit.getId()));
    }

    @Step("Получить количество блокировок по договору {deposit.numDog}")
    public long countHolds(Dto_Deposit deposit) {

        String sql = """
                SELECT COUNT(*)
                FROM Z#R2_DEP_HOLD h
                WHERE h.C_DEPOSIT = :depositId""";

        return dao.selectValue(sql, Long.class, Map.of("depositId", deposit.getId()));
    }

    @Step("Получить доступный остаток по договору {deposit.numDog}")
    public BigDecimal getAvailableBalance(Dto_Deposit deposit) {

        String sql = """
                SELECT a.C_SALDO - NVL(SUM(h.C_SUM), 0)
                FROM Z#R2_DEPOSIT d
                INNER JOIN Z#AC_FIN a ON a.ID = d.C_ACCOUNT
                LEFT JOIN Z#R2_DEP_HOLD h ON h.C_DEPOSIT = d.ID
                                         AND h.C_STATE = 'ACTIVE'
                                         AND h.C_DATE_BEGIN <= SYSDATE
                WHERE d.ID = :depositId
                GROUP BY a.C_SALDO""";

        return dao.selectValue(sql, BigDecimal.class, Map.of("depositId", deposit.getId()));
    }

    @Step("Обнулить остаток на счёте договора {deposit.numDog}")
    public void setZeroBalance(Dto_Deposit deposit) {

        String sql = """
                UPDATE Z#AC_FIN
                SET C_SALDO = 0
                WHERE ID = :accountId""";

        dao.executeUpdate(sql, Map.of("accountId", deposit.getAccountId()));
    }
}
