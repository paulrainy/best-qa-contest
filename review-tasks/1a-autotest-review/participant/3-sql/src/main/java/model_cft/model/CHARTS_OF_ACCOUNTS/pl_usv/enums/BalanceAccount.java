package model_cft.model.CHARTS_OF_ACCOUNTS.pl_usv.enums;

/**
 * Балансовые счета второго порядка.
 */
public enum BalanceAccount {

    $40817("40817", "Физические лица");

    private final String code;
    private final String description;

    BalanceAccount(String code, String description) {
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
