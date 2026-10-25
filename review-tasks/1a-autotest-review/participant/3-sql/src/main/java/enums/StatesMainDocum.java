package enums;

/**
 * Состояния документов.
 */
public enum StatesMainDocum {

    $TO_KASSA("TO_KASSA", "К кассе"),
    $PROV("PROV", "Проведён");

    private final String code;
    private final String description;

    StatesMainDocum(String code, String description) {
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
