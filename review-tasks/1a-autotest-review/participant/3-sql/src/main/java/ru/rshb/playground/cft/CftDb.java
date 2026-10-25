package ru.rshb.playground.cft;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;

/**
 * База одного стенда внутри процесса песочницы. Запросы заглушки написаны так, чтобы работать в обоих режимах H2:
 * имена таблиц в кавычках, параметры через «?».
 */
final class CftDb {

    final Stand stand;
    private final Connection connection;
    private final AtomicLong ids;

    CftDb(Stand stand) throws SQLException {
        this.stand = stand;
        this.ids = new AtomicLong(stand.idSequenceStart());
        this.connection = DriverManager.getConnection(stand.localJdbcUrl(), "sa", "");
    }

    long nextId() {
        return ids.incrementAndGet();
    }

    long statusId(String code) {
        return stand.statusIds().get(code);
    }

    synchronized void exec(String sql, Object... params) {
        try (PreparedStatement st = prepare(sql, params)) {
            st.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Ошибка запроса песочницы: " + sql, e);
        }
    }

    synchronized List<Map<String, Object>> rows(String sql, Object... params) {
        try (PreparedStatement st = prepare(sql, params); ResultSet rs = st.executeQuery()) {
            ResultSetMetaData meta = rs.getMetaData();
            List<Map<String, Object>> rows = new ArrayList<>();
            while (rs.next()) {
                Map<String, Object> row = new LinkedHashMap<>();
                for (int i = 1; i <= meta.getColumnCount(); i++) {
                    row.put(meta.getColumnLabel(i).toUpperCase(), rs.getObject(i));
                }
                rows.add(row);
            }
            return rows;
        } catch (SQLException e) {
            throw new IllegalStateException("Ошибка запроса песочницы: " + sql, e);
        }
    }

    Optional<Map<String, Object>> row(String sql, Object... params) {
        List<Map<String, Object>> rows = rows(sql, params);
        return rows.isEmpty() ? Optional.empty() : Optional.of(rows.get(0));
    }

    long count(String sql, Object... params) {
        return ((Number) rows(sql, params).get(0).values().iterator().next()).longValue();
    }

    private PreparedStatement prepare(String sql, Object... params) throws SQLException {
        PreparedStatement st = connection.prepareStatement(sql);
        for (int i = 0; i < params.length; i++) {
            Object p = params[i];
            if (p instanceof LocalDate date) {
                st.setObject(i + 1, java.sql.Date.valueOf(date));
            } else {
                st.setObject(i + 1, p);
            }
        }
        return st;
    }

    static Long asLong(Object value) {
        return value == null ? null : ((Number) value).longValue();
    }

    static BigDecimal asDecimal(Object value) {
        return value == null ? null : new BigDecimal(value.toString());
    }

    static LocalDate asDate(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof LocalDate date) {
            return date;
        }
        if (value instanceof java.sql.Date date) {
            return date.toLocalDate();
        }
        if (value instanceof java.sql.Timestamp ts) {
            return ts.toLocalDateTime().toLocalDate();
        }
        if (value instanceof java.time.LocalDateTime ldt) {
            return ldt.toLocalDate();
        }
        return LocalDate.parse(value.toString().substring(0, 10));
    }
}
