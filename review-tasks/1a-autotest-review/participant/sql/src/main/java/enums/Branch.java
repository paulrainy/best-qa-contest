package enums;

import java.util.Arrays;

/**
 * Филиалы банка.
 */
public enum Branch {

    $MOSCOW("3400", "Московский РФ"),
    $TVER("2600", "Тверской РФ"),
    $KALUGA("1500", "Калужский РФ");

    private final String code;
    private final String description;

    Branch(String code, String description) {
        this.code = code;
        this.description = description;
    }

    public String getCode() {
        return code;
    }

    public String getDescription() {
        return description;
    }

    public static Branch of(String code) {
        return Arrays.stream(values())
                .filter(b -> b.code.equals(code))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Неизвестный филиал: " + code));
    }
}
