package enums;

/**
 * Символы кассы.
 */
public enum CashboxSymbol {

    RECEIPTS_TO_CL_PRIV_DEPOSIT_ACCOUNT("16", "Поступления на счета по вкладам ФЛ");

    private final String code;
    private final String description;

    CashboxSymbol(String code, String description) {
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
