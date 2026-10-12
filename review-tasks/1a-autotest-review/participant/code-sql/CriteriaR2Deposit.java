package model_cft.model.PRODUCTS.r2_deposit;

import enums.Branch;
import model_cft.model.CLIENTS.clPriv.CriteriaClPriv;
import model_cft.model.CLIENTS.clPriv.DtoClPriv;
import model_cft.model.FINTOOLS.ft_money.enums.Currency;
import model_cft.model.ParametersBuilderBasic;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.REFERENCES.com_status_prd.enums.ComStatusPrd;
import model_cft.model.REFERENCES.r2_fin_product.enums.R2FinProduct;
import utils.builderSql.QueryBuilder;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Map;

/**
 * Билдер SQL-запроса для поиска договоров «Розница. Депозиты».
 */
public class CriteriaR2Deposit extends ParametersBuilderBasic<Dto_Deposit> {

    // ID записей справочника Z#COM_STATUS_PRD — чтобы не джойнить справочник в каждом запросе
    private static final Map<ComStatusPrd, Long> STATUS_IDS = Map.of(
            ComStatusPrd.$WAIT_CONF, 2047892L,
            ComStatusPrd.$WORK, 2047893L,
            ComStatusPrd.$CLOSE, 2047897L);

    public CriteriaR2Deposit() {

        super(Dto_Deposit.class);

        queryBuilder = new QueryBuilder()
                .select("d.*")
                .from("Z#R2_DEPOSIT d");
    }

    /**
     * Филиал договора.
     */
    public CriteriaR2Deposit withBranchEqualTo(Branch branch) {

        queryBuilder.where("d.C_FILIAL = '%s'".formatted(branch.getCode()));
        addParameter("Филиал", branch.getCode());

        return this;
    }

    /**
     * Состояние договора.
     */
    public CriteriaR2Deposit withStatusEqualTo(ComStatusPrd status) {

        queryBuilder.where("d.C_COM_STATUS = %d".formatted(STATUS_IDS.get(status)));
        addParameter("Состояние", status.getDescription());

        return this;
    }

    /**
     * Валюта договора.
     */
    public CriteriaR2Deposit withCurrencyEqualTo(Currency currency) {

        queryBuilder.where("d.C_CURRENCY = '%s'".formatted(currency.getCode()));
        addParameter("Валюта", currency.getCode());

        return this;
    }

    /**
     * Финансовый продукт.
     */
    public CriteriaR2Deposit withFinProductEqualTo(R2FinProduct finProduct) {

        queryBuilder.where("d.C_FIN_PRODUCT = '%s'".formatted(finProduct.getCode()));
        addParameter("Финансовый продукт", finProduct.getDescription());

        return this;
    }

    /**
     * Клиент договора.
     */
    public CriteriaR2Deposit withClientEqualTo(DtoClPriv clPriv) {

        queryBuilder.where("d.C_CLIENT = %d".formatted(clPriv.getId()));
        addParameter("Клиент", clPriv.getId());

        return this;
    }

    /**
     * Дата создания договора.
     */
    public CriteriaR2Deposit withCreateDateEqualTo(LocalDate date) {

        queryBuilder.where("d.C_DATE_CREATE = DATE '%s'".formatted(date));
        addParameter("Дата создания", date);

        return this;
    }

    /**
     * Остаток на счёте договора не меньше суммы.
     */
    public CriteriaR2Deposit withBalanceGreaterThanOrEqualTo(BigDecimal sum) {

        queryBuilder
                .join("INNER JOIN Z#AC_FIN a ON a.ID = d.C_ACCOUNT")
                .where("a.C_SALDO >= %s".formatted(sum.toPlainString()));
        addParameter("Остаток не меньше", sum);

        return this;
    }

    /**
     * По договору нет действующих блокировок.
     */
    public CriteriaR2Deposit withoutActiveHold() {

        queryBuilder
                .join("LEFT JOIN Z#R2_DEP_HOLD h ON h.C_DEPOSIT = d.ID AND h.C_STATE = 'ACTIVE'")
                .where("h.ID IS NULL");
        addParameter("Действующие блокировки", "нет");

        return this;
    }

    /**
     * К договору не выпущено действующих карт.
     */
    public CriteriaR2Deposit withoutActiveCard() {

        queryBuilder
                .join("LEFT JOIN Z#R2_IP_CARDS ic ON ic.C_DEPOSIT = d.ID")
                .where("ic.C_STATE <> 'ACTIVE'");
        addParameter("Действующие карты", "нет");

        return this;
    }

    /**
     * Дополнительные условия на клиента договора.
     */
    public CriteriaR2Deposit joinClPriv(CriteriaClPriv clPrivCriteria) {

        queryBuilder
                .join("INNER JOIN Z#CL_PRIV cp ON cp.ID = d.C_CLIENT")
                .join(clPrivCriteria.getQueryBuilder());
        addParameter("Клиент", clPrivCriteria.getParametersAsString());

        return this;
    }
}
