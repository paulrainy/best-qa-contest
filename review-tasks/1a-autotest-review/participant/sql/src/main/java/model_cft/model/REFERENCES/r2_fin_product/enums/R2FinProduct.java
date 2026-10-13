package model_cft.model.REFERENCES.r2_fin_product.enums;

/**
 * Финансовые продукты «Розница. Депозиты».
 */
public enum R2FinProduct {

    $ALL_TEK_ALL_AL("ALL_TEK_ALL_AL", "Текущий счёт"),
    $NAK_SCHET("NAK_SCHET", "Накопительный счёт");

    private final String code;
    private final String description;

    R2FinProduct(String code, String description) {
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
