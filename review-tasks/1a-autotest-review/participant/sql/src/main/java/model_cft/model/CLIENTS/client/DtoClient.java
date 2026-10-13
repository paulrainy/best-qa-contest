package model_cft.model.CLIENTS.client;

import model_cft.model.Rows;

import java.util.Map;

/**
 * Клиент — строка Z#CLIENT.
 */
public class DtoClient {

    private final Long id;
    private final String name;
    private final String filial;
    private final boolean resident;

    DtoClient(Map<String, Object> row) {
        this.id = Rows.id(row, "ID");
        this.name = Rows.text(row, "C_NAME");
        this.filial = Rows.text(row, "C_FILIAL");
        this.resident = "1".equals(Rows.text(row, "C_IS_RESIDENT"));
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getFilial() {
        return filial;
    }

    public boolean isResident() {
        return resident;
    }

    @Override
    public String toString() {
        return "клиент %s (ID %d)".formatted(name, id);
    }
}
