package model_cft.model.ACCOUNTS.ac_fin;

import model_cft.model.Rows;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Лицевой счёт — строка Z#AC_FIN, с кодом состояния из справочника.
 */
public class DtoAcFin {

    private final Long id;
    private final String number;
    private final BigDecimal saldo;
    private final String statusCode;

    DtoAcFin(Map<String, Object> row) {
        this.id = Rows.id(row, "ID");
        this.number = Rows.text(row, "C_MAIN_V_ID");
        this.saldo = Rows.decimal(row.get("C_SALDO"));
        this.statusCode = Rows.text(row, "STATUS_CODE");
    }

    public Long getId() {
        return id;
    }

    public String getNumber() {
        return number;
    }

    public BigDecimal getSaldo() {
        return saldo;
    }

    public String getStatusCode() {
        return statusCode;
    }
}
