package utils.asserts;

import io.qameta.allure.Allure;

/**
 * Общие проверки объектов ЦФТ.
 */
public class CftObjectAssert<S extends CftObjectAssert<S, T>, T> {

    protected final T actual;
    private final String what;

    protected CftObjectAssert(T actual, String what) {
        this.actual = actual;
        this.what = what;
    }

    @SuppressWarnings("unchecked")
    protected S self() {
        return (S) this;
    }

    public S objectExist() {
        Allure.step("Проверить: " + what + " найден", () -> {
            if (actual == null) {
                throw new AssertionError(what + " не найден: подходящих данных на стенде нет, см. параметры поиска в логе");
            }
        });
        return self();
    }

    public S objectNotExist() {
        Allure.step("Проверить: " + what + " не найден", () -> {
            if (actual != null) {
                throw new AssertionError(what + " найден, а не должен: " + actual);
            }
        });
        return self();
    }

    protected T requireActual() {
        if (actual == null) {
            throw new AssertionError(what + " не найден");
        }
        return actual;
    }
}
