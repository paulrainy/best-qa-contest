package model_cft.model.PRODUCTS.r2_deposit.entities;

import model_cft.model.ACCOUNTS.ac_fin.DtoAcFin;
import model_cft.model.DaoCommon;
import model_cft.model.Rows;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Map;

/**
 * Договор «Розница. Депозиты» — строка Z#R2_DEPOSIT.
 */
public class Dto_Deposit {

    private Long id;
    private String numDog;
    private Long clientId;
    private Long statusId;
    private String currency;
    private String finProduct;
    private String filial;
    private Long depart;
    private Long accountId;
    private LocalDate dateCreate;
    private LocalDate dateClose;

    Dto_Deposit(Map<String, Object> row) {
        id = Rows.id(row, "ID");
        numDog = Rows.text(row, "C_NUM_DOG");
        clientId = Rows.id(row, "C_CLIENT");
        statusId = Rows.id(row, "C_COM_STATUS");
        currency = Rows.text(row, "C_CURRENCY");
        finProduct = Rows.text(row, "C_FIN_PRODUCT");
        filial = Rows.text(row, "C_FILIAL");
        depart = Rows.id(row, "C_DEPART");
        accountId = Rows.id(row, "C_ACCOUNT");
        dateCreate = Rows.date(row.get("C_DATE_CREATE"));
        dateClose = Rows.date(row.get("C_DATE_CLOSE"));
    }

    /**
     * Перечитывает договор из БД.
     */
    public Dto_Deposit update() {
        Dto_Deposit fresh = DaoCommon.getInstance().selectOne("SELECT * FROM Z#R2_DEPOSIT WHERE ID = :id",
                Dto_Deposit.class, Map.of("id", id));
        numDog = fresh.numDog;
        clientId = fresh.clientId;
        statusId = fresh.statusId;
        currency = fresh.currency;
        finProduct = fresh.finProduct;
        filial = fresh.filial;
        depart = fresh.depart;
        accountId = fresh.accountId;
        dateCreate = fresh.dateCreate;
        dateClose = fresh.dateClose;
        return this;
    }

    /**
     * Остаток на счёте договора.
     */
    public BigDecimal getBalance() {
        return DaoCommon.getInstance().selectValue("SELECT C_SALDO FROM Z#AC_FIN WHERE ID = :id", BigDecimal.class,
                Map.of("id", accountId));
    }

    /**
     * Код состояния договора из справочника Z#COM_STATUS_PRD.
     */
    public String getStatusCode() {
        return DaoCommon.getInstance().selectValue("SELECT C_CODE FROM Z#COM_STATUS_PRD WHERE ID = :id", String.class,
                Map.of("id", statusId));
    }

    /**
     * Счёт договора.
     */
    public DtoAcFin getAccount() {
        return DaoCommon.getInstance().selectOne("""
                SELECT a.*, s.C_CODE AS STATUS_CODE
                FROM Z#AC_FIN a
                INNER JOIN Z#COM_STATUS_PRD s ON s.ID = a.C_COM_STATUS
                WHERE a.ID = :id""", DtoAcFin.class, Map.of("id", accountId));
    }

    public Long getId() {
        return id;
    }

    public String getNumDog() {
        return numDog;
    }

    public Long getClientId() {
        return clientId;
    }

    public String getCurrency() {
        return currency;
    }

    public String getFinProduct() {
        return finProduct;
    }

    public String getFilial() {
        return filial;
    }

    /**
     * Подразделение договора.
     */
    public Long getLinkDepart() {
        return depart;
    }

    public Long getAccountId() {
        return accountId;
    }

    public LocalDate getDateCreate() {
        return dateCreate;
    }

    public LocalDate getDateClose() {
        return dateClose;
    }

    @Override
    public String toString() {
        return "договор № %s (ID %d)".formatted(numDog, id);
    }
}
