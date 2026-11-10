package reference;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import java.sql.SQLException;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import reference.support.*;

class TransferTest extends BaseTest {
    @Test
    void readinessAndReadOnlyConnections() throws Exception {
        assertEquals("UP", api.get("/api/v1/health").get("status").asText());
        assertFalse(db.query("SELECT client_id FROM clients LIMIT 1").isEmpty());
        var p = data.own();
        try (var connection = db.open();
                var statement = connection.prepareStatement(
                        "UPDATE accounts SET balance=balance WHERE account_number=?")) {
            statement.setString(1, p.fromNumber());
            assertThrows(SQLException.class, statement::executeUpdate);
        }
        try (var probe = AmqpProbe.subscribe("transfer.created")) {
            assertFalse(probe.queueName().isBlank());
        }
    }
    @Test
    void ownTransferCompletesWithExactBalances() throws Exception {
        var p = data.own();
        var t = complete(start(p, "100.00"));
        assertEquals("OWN", t.get("transferType").asText());
        money("0", t.get("commission").decimalValue());
        money("999900", api.balance(p.fromNumber()));
        money("1000100", api.balance(p.toNumber()));
        assertEquals(2, db.postings(id(t)).size());
    }
    @Test
    void otherTransferWithinFreeThreshold() throws Exception {
        var p = data.other();
        var t = complete(start(p, "100.01"));
        assertEquals("OTHER", t.get("transferType").asText());
        money("0", t.get("commission").decimalValue());
        money("999899.99", api.balance(p.fromNumber()));
        money("1000100.01", api.balance(p.toNumber()));
    }
    @Test
    void insufficientFundsLeaveNoTransfer() throws Exception {
        var a = api.createAccount(BigDecimal.ZERO, null, "ACTIVE");
        var b = api.createAccount(BigDecimal.ZERO, null, "ACTIVE");
        var response = api.createTransfer(a.get("accountNumber").asText(), b.get("accountNumber").asText(),
                new BigDecimal("100"), UUID.randomUUID().toString());
        assertEquals(422, response.statusCode());
        assertEquals("INSUFFICIENT_FUNDS", api.json(response).get("code").asText());
        money("0", api.balance(a.get("accountNumber").asText()));
        money("0", api.balance(b.get("accountNumber").asText()));
        assertEquals(0L,
                ((Number) db.query("SELECT COUNT(*) AS c FROM transfers WHERE from_account=?",
                                    a.get("accountNumber").asText())
                                .get(0)
                                .get("c"))
                        .longValue());
    }
}
