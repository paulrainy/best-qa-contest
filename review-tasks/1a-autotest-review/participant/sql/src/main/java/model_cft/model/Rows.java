package model_cft.model;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Map;

/**
 * Чтение значений из строки результата.
 */
public final class Rows {

    private Rows() {
    }

    public static Long id(Map<String, Object> row, String column) {
        Object value = row.get(column);
        return value == null ? null : ((Number) value).longValue();
    }

    public static String text(Map<String, Object> row, String column) {
        Object value = row.get(column);
        return value == null ? null : value.toString();
    }

    public static BigDecimal decimal(Object value) {
        return value == null ? null : new BigDecimal(value.toString());
    }

    public static LocalDate date(Object value) {
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
