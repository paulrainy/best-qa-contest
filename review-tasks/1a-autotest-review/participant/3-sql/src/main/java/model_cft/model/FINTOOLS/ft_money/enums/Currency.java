package model_cft.model.FINTOOLS.ft_money.enums;

/**
 * Валюты.
 */
public enum Currency {

    RUB("810"),
    USD("840");

    private final String code;

    Currency(String code) {
        this.code = code;
    }

    public String getCode() {
        return code;
    }
}
