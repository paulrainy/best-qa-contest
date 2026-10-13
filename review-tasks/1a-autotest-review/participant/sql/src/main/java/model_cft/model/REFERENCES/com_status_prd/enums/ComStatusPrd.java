package model_cft.model.REFERENCES.com_status_prd.enums;

/**
 * Состояния договоров и счетов: коды справочника Z#COM_STATUS_PRD.
 */
public enum ComStatusPrd {

    $WAIT_CONF("WAIT_CONF", "Ожидает подтверждения"),
    $WORK("WORK", "Работает"),
    $OPEN("OPEN", "Открыт"),
    $CLOSE("CLOSE", "Закрыт");

    private final String code;
    private final String description;

    ComStatusPrd(String code, String description) {
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
