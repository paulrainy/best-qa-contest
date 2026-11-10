package reference.support;

import java.sql.*;
import java.util.*;

public final class DbProbe {
    private final StandConfig config;
    public DbProbe(StandConfig config) {
        this.config = config;
    }
    public Connection open() throws SQLException {
        return DriverManager.getConnection(config.dbUrl(), config.dbUser(), config.dbPassword());
    }
    public List<Map<String, Object>> query(String sql, Object... parameters) throws SQLException {
        try (Connection connection = open(); PreparedStatement statement = connection.prepareStatement(sql)) {
            for (int i = 0; i < parameters.length; i++) statement.setObject(i + 1, parameters[i]);
            try (ResultSet rs = statement.executeQuery()) {
                List<Map<String, Object>> rows = new ArrayList<>();
                while (rs.next()) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    for (int i = 1; i <= rs.getMetaData().getColumnCount(); i++)
                        row.put(rs.getMetaData().getColumnLabel(i).toLowerCase(Locale.ROOT), rs.getObject(i));
                    rows.add(row);
                }
                return rows;
            }
        }
    }
    public List<Map<String, Object>> postings(UUID id) throws SQLException {
        return query("SELECT * FROM postings WHERE transfer_id=? ORDER BY posting_id", id);
    }
}
