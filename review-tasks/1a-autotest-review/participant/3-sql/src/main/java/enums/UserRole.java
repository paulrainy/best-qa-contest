package enums;

/**
 * Роли пользователей ЦФТ.
 */
public enum UserRole {

    $OPER_FL("OPER_FL", "Операционист ФЛ"),
    $CASHIER("CASHIER", "Кассир");

    private final String code;
    private final String description;

    UserRole(String code, String description) {
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
