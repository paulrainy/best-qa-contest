package model_cft.model.CLIENTS.clPriv;

import model_cft.model.CLIENTS.client.DtoClient;
import model_cft.model.DaoCommon;
import model_cft.model.Rows;

import java.time.LocalDate;
import java.util.Map;

/**
 * Клиент ФЛ — строка Z#CL_PRIV.
 */
public class DtoClPriv {

    private final Long id;
    private final LocalDate docDateEnd;
    private final LocalDate deathDate;
    private DtoClient client;

    DtoClPriv(Map<String, Object> row) {
        this.id = Rows.id(row, "ID");
        this.docDateEnd = Rows.date(row.get("C_DOC_DATE_END"));
        this.deathDate = Rows.date(row.get("C_DEATH_DATE"));
    }

    public Long getId() {
        return id;
    }

    public LocalDate getDocDateEnd() {
        return docDateEnd;
    }

    public LocalDate getDeathDate() {
        return deathDate;
    }

    /**
     * Карточка клиента из Z#CLIENT.
     */
    public DtoClient getClient() {
        if (client == null) {
            client = DaoCommon.getInstance().selectOne("SELECT * FROM Z#CLIENT WHERE ID = :id", DtoClient.class,
                    Map.of("id", id));
        }
        return client;
    }

    @Override
    public String toString() {
        return "клиент ФЛ %s (ID %d, ДУЛ до %s)".formatted(getClient().getName(), id, docDateEnd);
    }
}
