package enums;

/**
 * Состояния фактических операций.
 */
public enum StatesFactOper {

    $ADDITIONAL_CONTROL("ADD_CONTROL", "На дополнительном контроле"),
    $PERFORMED("PERFORMED", "Выполнена");

    private final String code;
    private final String description;

    StatesFactOper(String code, String description) {
        this.code = code;
        this.description = description;
    }

    public String getCode() {
        return code;
    }

    public String getDescription() {
        return description;
    }
}
