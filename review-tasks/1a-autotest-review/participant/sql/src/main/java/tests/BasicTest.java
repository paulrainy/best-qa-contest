package tests;

import CFT.api.CftApi;
import enums.Branch;
import io.qameta.allure.Allure;
import model_cft.model.DaoCommon;
import model_cft.model.user.Dto_User;
import org.testng.annotations.BeforeSuite;
import ru.rshb.playground.cft.CftSandbox;
import ru.rshb.playground.cft.Stand;

import java.time.LocalDate;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/**
 * Базовый класс тестов ЦФТ.
 */
public class BasicTest {

    /**
     * Поднимает песочницу, если она ещё не запущена отдельно через mvn exec:java.
     */
    @BeforeSuite(alwaysRun = true)
    public void startSandbox() {
        CftSandbox.startIfNotRunning();
    }

    /**
     * Вход в ЦФТ под пользователем.
     */
    protected void authorization(Dto_User user) {
        String login = user.getLogin();
        Allure.step("Авторизация в ЦФТ: " + user, () -> {
            CftApi.login(login, Stand.PASSWORD);
        });
    }

    /**
     * Операционный день пользователя, который вошёл последним.
     */
    protected LocalDate getOperDay() {
        return CftApi.session().operDay();
    }

    /**
     * Продуктовые филиалы, у которых операционный день совпадает с текущей датой.
     */
    protected List<Branch> getProductBranchesWithCheckOperDayEqualCurrDay() {
        List<String> codes = DaoCommon.getInstance().selectList(
                "SELECT C_CODE FROM Z#BRANCH WHERE C_OPER_DAY = :today", String.class,
                Map.of("today", LocalDate.now()));
        return Arrays.stream(Branch.values()).filter(b -> codes.contains(b.getCode())).toList();
    }
}
