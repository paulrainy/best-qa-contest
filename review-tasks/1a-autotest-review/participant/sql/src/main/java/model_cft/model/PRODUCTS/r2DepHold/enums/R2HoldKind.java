package model_cft.model.PRODUCTS.r2DepHold.enums;

/**
 * Виды блокировок сумм по договору.
 */
public enum R2HoldKind {

    $ARREST("ARREST", "Арест"),
    $BLOCK("BLOCK", "Блокировка");

    private final String code;
    private final String description;

    R2HoldKind(String code, String description) {
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
