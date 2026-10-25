package model_cft.model.CLIENTS.clPriv;

import enums.Branch;
import model_cft.model.ParametersBuilderBasic;
import utils.builderSql.QueryBuilder;

import java.time.LocalDate;

/**
 * Билдер SQL-запроса для поиска клиентов ФЛ.
 */
public class CriteriaClPriv extends ParametersBuilderBasic<DtoClPriv> {

    public CriteriaClPriv() {

        super(DtoClPriv.class);

        queryBuilder = new QueryBuilder()
                .select("cp.*")
                .from("Z#CL_PRIV cp")
                .join("INNER JOIN Z#CLIENT c ON c.ID = cp.ID");
    }

    /**
     * Филиал клиента.
     */
    public CriteriaClPriv withBranchEqualTo(Branch branch) {

        queryBuilder.where("c.C_FILIAL = '%s'".formatted(branch.getCode()));
        addParameter("Филиал", branch.getCode());

        return this;
    }

    /**
     * Клиент — резидент РФ.
     */
    public CriteriaClPriv withResident() {

        queryBuilder.where("c.C_IS_RESIDENT = '1'");
        addParameter("Резидент", "да");

        return this;
    }

    /**
     * Клиент жив.
     */
    public CriteriaClPriv withAlive() {

        queryBuilder.where("cp.C_DEATH_DATE IS NULL");
        addParameter("Жив", "да");

        return this;
    }

    /**
     * Имя клиента не равно.
     */
    public CriteriaClPriv withNameNotEqualTo(String name) {

        queryBuilder.where("c.C_NAME <> '%s'".formatted(name));
        addParameter("Имя клиента не равно", name);

        return this;
    }

    /**
     * Срок действия ДУЛ не истёк на дату.
     */
    public CriteriaClPriv withDocDateEndNotExpired(LocalDate date) {

        queryBuilder.where("cp.C_DOC_DATE_END >= DATE '%s'".formatted(date));
        addParameter("ДУЛ действует на дату", date);

        return this;
    }

    /**
     * Срок действия ДУЛ истёк на дату.
     */
    public CriteriaClPriv withDocDateEndExpired(LocalDate date) {

        queryBuilder.where("cp.C_DOC_DATE_END < DATE '%s'".formatted(date));
        addParameter("ДУЛ истёк на дату", date);

        return this;
    }

    /**
     * У клиента нет блокировок.
     */
    public CriteriaClPriv withoutBlocks() {

        queryBuilder.where("""
                NOT EXISTS (SELECT 1
                            FROM Z#CL_BLOCK b
                            WHERE b.C_CLIENT = cp.ID)""");
        addParameter("Блокировки", "нет");

        return this;
    }

    /**
     * У клиента заполнена форма CRS.
     */
    public CriteriaClPriv withCrs() {

        queryBuilder.where("""
                EXISTS (SELECT 1
                        FROM Z#SHB_FORMA_CRS f
                        WHERE f.C_CLIENT = cp.ID
                          AND f.C_CRS_STATUS IS NOT NULL)""");
        addParameter("Форма CRS", "есть");

        return this;
    }
}
