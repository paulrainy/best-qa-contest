package utils;

import model_cft.model.CLIENTS.clPriv.DtoClPriv;
import model_cft.model.PRODUCTS.fact_oper.entities.DtoR2FactOper;
import model_cft.model.PRODUCTS.r2_deposit.entities.Dto_Deposit;
import model_cft.model.user.Dto_User;
import utils.asserts.DepositAssert;
import utils.asserts.FactOperAssert;
import utils.asserts.ObjectAssert;

/**
 * Проверки объектов ЦФТ по данным БД.
 */
public final class AssertionsUtil {

    private AssertionsUtil() {
    }

    public static DepositAssert assertThat(Dto_Deposit deposit) {
        return new DepositAssert(deposit);
    }

    public static FactOperAssert assertThat(DtoR2FactOper factOper) {
        return new FactOperAssert(factOper);
    }

    public static ObjectAssert<DtoClPriv> assertThat(DtoClPriv clPriv) {
        return new ObjectAssert<>(clPriv, "Клиент ФЛ");
    }

    public static ObjectAssert<Dto_User> assertThat(Dto_User user) {
        return new ObjectAssert<>(user, "Пользователь");
    }
}
