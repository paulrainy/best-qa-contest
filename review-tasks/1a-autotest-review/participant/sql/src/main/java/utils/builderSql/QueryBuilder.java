package utils.builderSql;

import enums.TypeDb;

import java.util.ArrayList;
import java.util.List;

/**
 * Собирает SELECT. Условия WHERE соединяются через AND, каждое берётся в скобки.
 * Ограничение числа строк добавляется в синтаксисе СУБД стенда.
 */
public class QueryBuilder {

    private String select = "*";
    private String from;
    private final List<String> joins = new ArrayList<>();
    private final List<String> wheres = new ArrayList<>();

    public QueryBuilder select(String select) {
        this.select = select;
        return this;
    }

    public QueryBuilder from(String from) {
        this.from = from;
        return this;
    }

    public QueryBuilder join(String join) {
        joins.add(join);
        return this;
    }

    /**
     * Переносит в запрос JOIN и условия WHERE другого билдера.
     */
    public QueryBuilder join(QueryBuilder other) {
        joins.addAll(other.joins);
        wheres.addAll(other.wheres);
        return this;
    }

    public QueryBuilder where(String condition) {
        wheres.add(condition);
        return this;
    }

    /**
     * Текст запроса. limit — сколько строк вернуть, null — без ограничения.
     */
    public String build(Integer limit, TypeDb typeDb) {
        List<String> conditions = new ArrayList<>();
        for (String where : wheres) {
            conditions.add("(" + where + ")");
        }
        if (limit != null && typeDb == TypeDb.ORACLE) {
            conditions.add("ROWNUM <= " + limit);
        }
        StringBuilder sql = new StringBuilder("SELECT ").append(select).append("\nFROM ").append(from);
        for (String join : joins) {
            sql.append("\n").append(join);
        }
        if (!conditions.isEmpty()) {
            sql.append("\nWHERE ").append(String.join("\n  AND ", conditions));
        }
        if (limit != null && typeDb == TypeDb.POSTGRE) {
            sql.append("\nLIMIT ").append(limit);
        }
        return sql.toString();
    }
}
