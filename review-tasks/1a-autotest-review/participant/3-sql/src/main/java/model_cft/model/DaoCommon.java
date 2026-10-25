package model_cft.model;

import enums.TypeDb;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import ru.rshb.playground.cft.CftSandbox;
import ru.rshb.playground.cft.Stand;

import java.lang.reflect.Constructor;
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
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Выполняет запросы к БД стенда. Текст запроса уходит в БД как есть, «:имя» — bind-переменная из переданной Map.
 * На стендах PostgreSQL имена таблиц с «#» берутся в кавычки: без них PostgreSQL читает «#» как оператор.
 */
public final class DaoCommon {

    private static final Logger log = LogManager.getLogger(DaoCommon.class);
    private static final Pattern BIND = Pattern.compile("(?<![:\\w]):(\\w+)");
    private static final Pattern HASH_TABLE = Pattern.compile("(?<![\"\\w])(Z#\\w+)", Pattern.CASE_INSENSITIVE);

    private static DaoCommon instance;

    private final Stand stand;

    private DaoCommon(Stand stand) {
        this.stand = stand;
    }

    public static synchronized DaoCommon getInstance() {
        Stand stand = Stand.current();
        if (instance == null || instance.stand != stand) {
            CftSandbox.startIfNotRunning();
            instance = new DaoCommon(stand);
        }
        return instance;
    }

    public TypeDb getTypeDb() {
        return stand.getTypeDb();
    }

    /**
     * Первая строка результата или null.
     */
    public <T> T selectOne(String sql, Class<T> type, Map<String, ?> params) {
        List<T> rows = selectList(sql, type, params);
        return rows.isEmpty() ? null : rows.get(0);
    }

    /**
     * Значение из первой колонки первой строки или null.
     */
    public <T> T selectValue(String sql, Class<T> type, Map<String, ?> params) {
        return selectOne(sql, type, params);
    }

    public <T> List<T> selectList(String sql, Class<T> type, Map<String, ?> params) {
        List<T> result = new ArrayList<>();
        for (Map<String, Object> row : query(sql, params)) {
            result.add(convert(row, type));
        }
        return result;
    }

    /**
     * Выполняет запрос и фиксирует изменения.
     */
    public int executeUpdate(String sql, Map<String, ?> params) {
        List<String> names = new ArrayList<>();
        String prepared = prepare(sql, names);
        try (Connection connection = connect(); PreparedStatement st = connection.prepareStatement(prepared)) {
            bind(st, names, params);
            int count = st.executeUpdate();
            log.debug("{} строк изменено:\n{}", count, prepared);
            return count;
        } catch (SQLException e) {
            throw new IllegalStateException("Ошибка запроса к БД стенда " + stand + ": " + e.getMessage()
                    + "\n" + prepared, e);
        }
    }

    private List<Map<String, Object>> query(String sql, Map<String, ?> params) {
        List<String> names = new ArrayList<>();
        String prepared = prepare(sql, names);
        try (Connection connection = connect(); PreparedStatement st = connection.prepareStatement(prepared)) {
            bind(st, names, params);
            try (ResultSet rs = st.executeQuery()) {
                ResultSetMetaData meta = rs.getMetaData();
                List<Map<String, Object>> rows = new ArrayList<>();
                while (rs.next()) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    for (int i = 1; i <= meta.getColumnCount(); i++) {
                        row.putIfAbsent(meta.getColumnLabel(i).toUpperCase(), rs.getObject(i));
                    }
                    rows.add(row);
                }
                return rows;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Ошибка запроса к БД стенда " + stand + ": " + e.getMessage()
                    + "\n" + prepared, e);
        }
    }

    private Connection connect() throws SQLException {
        return DriverManager.getConnection(stand.jdbcUrl(), "sa", "");
    }

    private String prepare(String sql, List<String> names) {
        String text = sql;
        if (stand.getTypeDb() == TypeDb.POSTGRE) {
            text = HASH_TABLE.matcher(text).replaceAll(m -> Matcher.quoteReplacement("\"" + m.group(1).toUpperCase() + "\""));
        }
        Matcher m = BIND.matcher(text);
        StringBuilder out = new StringBuilder();
        while (m.find()) {
            names.add(m.group(1));
            m.appendReplacement(out, "?");
        }
        m.appendTail(out);
        return out.toString();
    }

    private static void bind(PreparedStatement st, List<String> names, Map<String, ?> params) throws SQLException {
        for (int i = 0; i < names.size(); i++) {
            if (params == null || !params.containsKey(names.get(i))) {
                throw new IllegalArgumentException("Не передано значение bind-переменной :" + names.get(i));
            }
            Object value = params.get(names.get(i));
            st.setObject(i + 1, value instanceof LocalDate date ? java.sql.Date.valueOf(date) : value);
        }
    }

    @SuppressWarnings("unchecked")
    private static <T> T convert(Map<String, Object> row, Class<T> type) {
        Object first = row.isEmpty() ? null : row.values().iterator().next();
        if (type == Long.class) {
            return (T) (first == null ? null : Long.valueOf(((Number) first).longValue()));
        }
        if (type == Integer.class) {
            return (T) (first == null ? null : Integer.valueOf(((Number) first).intValue()));
        }
        if (type == BigDecimal.class) {
            return (T) Rows.decimal(first);
        }
        if (type == String.class) {
            return (T) (first == null ? null : first.toString());
        }
        if (type == LocalDate.class) {
            return (T) Rows.date(first);
        }
        try {
            Constructor<T> constructor = type.getDeclaredConstructor(Map.class);
            constructor.setAccessible(true);
            return constructor.newInstance(row);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("Не удалось создать " + type.getSimpleName() + " из строки " + row, e);
        }
    }
}
