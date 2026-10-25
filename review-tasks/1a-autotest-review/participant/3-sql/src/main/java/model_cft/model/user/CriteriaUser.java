package model_cft.model.user;

import enums.Branch;
import enums.UserRole;
import model_cft.model.ParametersBuilderBasic;
import utils.builderSql.QueryBuilder;

import java.util.Arrays;
import java.util.stream.Collectors;

/**
 * Поиск пользователей ЦФТ.
 */
public class CriteriaUser extends ParametersBuilderBasic<Dto_User> {

    public CriteriaUser() {

        super(Dto_User.class);

        queryBuilder = new QueryBuilder()
                .select("u.*")
                .from("Z#USER u");
    }

    public CriteriaUser withUnitEq(Branch branch) {

        queryBuilder.where("u.C_FILIAL = '%s'".formatted(branch.getCode()));
        addParameter("Филиал", branch.getCode());

        return this;
    }

    public CriteriaUser withDepartEq(Long depart) {

        queryBuilder.where("u.C_DEPART = %d".formatted(depart));
        addParameter("Подразделение", depart);

        return this;
    }

    public CriteriaUser withRoles(UserRole... roles) {

        String codes = Arrays.stream(roles).map(r -> "'" + r.getCode() + "'").collect(Collectors.joining(", "));
        queryBuilder.where("""
                EXISTS (SELECT 1
                        FROM Z#USER_ROLE r
                        WHERE r.C_USER = u.ID
                          AND r.C_ROLE IN (%s))""".formatted(codes));
        addParameter("Роли", Arrays.stream(roles).map(UserRole::getDescription).collect(Collectors.joining(", ")));

        return this;
    }

    /**
     * Случайный пользователь с нужной ролью или null.
     */
    public Dto_User findUser() {
        return getRandomObject(10);
    }
}
