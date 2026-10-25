package model_cft.model.DOCUMENTS.main_docum;

import model_cft.model.DaoCommon;
import model_cft.model.Rows;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Документ — строка Z#MAIN_DOCUM.
 */
public class DtoMainDocum {

    private Long id;
    private BigDecimal sum;
    private String state;

    DtoMainDocum(Map<String, Object> row) {
        this.id = Rows.id(row, "ID");
        this.sum = Rows.decimal(row.get("C_SUM"));
        this.state = Rows.text(row, "C_STATE");
    }

    /**
     * Перечитывает документ из БД.
     */
    public DtoMainDocum update() {
        DtoMainDocum fresh = DaoCommon.getInstance().selectOne("SELECT * FROM Z#MAIN_DOCUM WHERE ID = :id",
                DtoMainDocum.class, Map.of("id", id));
        this.sum = fresh.sum;
        this.state = fresh.state;
        return this;
    }

    public Long getId() {
        return id;
    }

    public BigDecimal getSum() {
        return sum;
    }

    public String getState() {
        return state;
    }

    @Override
    public String toString() {
        return "документ ID %d на %s".formatted(id, sum);
    }
}
