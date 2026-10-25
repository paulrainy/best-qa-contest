package model_cft.model.PRODUCTS.fact_oper.entities;

import model_cft.model.DOCUMENTS.main_docum.DtoMainDocum;
import model_cft.model.DaoCommon;
import model_cft.model.Rows;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Map;

/**
 * Фактическая операция по договору — строка Z#R2_FACT_OPER.
 */
public class DtoR2FactOper {

    private Long id;
    private Long depositId;
    private BigDecimal sum;
    private String state;
    private LocalDate date;
    private Long mainDocumId;

    DtoR2FactOper(Map<String, Object> row) {
        this.id = Rows.id(row, "ID");
        this.depositId = Rows.id(row, "C_DEPOSIT");
        this.sum = Rows.decimal(row.get("C_SUM"));
        this.state = Rows.text(row, "C_STATE");
        this.date = Rows.date(row.get("C_DATE"));
        this.mainDocumId = Rows.id(row, "C_MAIN_DOCUM");
    }

    /**
     * Перечитывает операцию из БД.
     */
    public DtoR2FactOper update() {
        DtoR2FactOper fresh = DaoCommon.getInstance().selectOne("SELECT * FROM Z#R2_FACT_OPER WHERE ID = :id",
                DtoR2FactOper.class, Map.of("id", id));
        this.sum = fresh.sum;
        this.state = fresh.state;
        this.date = fresh.date;
        this.mainDocumId = fresh.mainDocumId;
        return this;
    }

    /**
     * Документ операции.
     */
    public DtoMainDocum getMainDocum() {
        return DaoCommon.getInstance().selectOne("SELECT * FROM Z#MAIN_DOCUM WHERE ID = :id", DtoMainDocum.class,
                Map.of("id", mainDocumId));
    }

    public Long getId() {
        return id;
    }

    public Long getDepositId() {
        return depositId;
    }

    public BigDecimal getSum() {
        return sum;
    }

    public String getState() {
        return state;
    }

    public LocalDate getDate() {
        return date;
    }

    @Override
    public String toString() {
        return "фактическая операция ID %d от %s на %s".formatted(id, date, sum);
    }
}
