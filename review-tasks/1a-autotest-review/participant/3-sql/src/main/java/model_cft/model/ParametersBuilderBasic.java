package model_cft.model;

import io.qameta.allure.Allure;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import utils.builderSql.QueryBuilder;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

/**
 * Базовый класс Criteria-классов: поиск тестовых данных SQL-запросом.
 * Параметры поиска, текст запроса и выбранный объект пишутся в лог и в Allure.
 */
public abstract class ParametersBuilderBasic<T> {

    private static final Logger log = LogManager.getLogger(ParametersBuilderBasic.class);

    private final Class<T> type;
    private final Map<String, Object> parameters = new LinkedHashMap<>();

    protected QueryBuilder queryBuilder;

    protected ParametersBuilderBasic(Class<T> type) {
        this.type = type;
    }

    /**
     * Подпись условия для лога и Allure, на запрос не влияет.
     */
    protected void addParameter(String name, Object value) {
        parameters.put(name, value);
    }

    public QueryBuilder getQueryBuilder() {
        return queryBuilder;
    }

    public String getParametersAsString() {
        return parameters.entrySet().stream()
                .map(e -> e.getKey() + ": " + e.getValue())
                .collect(Collectors.joining("; "));
    }

    /**
     * Первая строка результата или null.
     */
    public T getObject() {
        List<T> found = search(1);
        return found.isEmpty() ? null : found.get(0);
    }

    /**
     * Случайный объект из первых n строк или null. Так параллельные прогоны берут разные данные.
     */
    public T getRandomObject(int n) {
        List<T> found = search(n);
        if (found.isEmpty()) {
            return null;
        }
        T chosen = found.get(ThreadLocalRandom.current().nextInt(found.size()));
        log.info("Выбран {}", chosen);
        Allure.addAttachment("Выбран", "text/plain", String.valueOf(chosen));
        return chosen;
    }

    private List<T> search(int limit) {
        DaoCommon dao = DaoCommon.getInstance();
        String sql = queryBuilder.build(limit, dao.getTypeDb());
        String name = "Поиск " + type.getSimpleName() + ": " + getParametersAsString();
        return Allure.step(name, () -> {
            Allure.addAttachment("SQL", "text/plain", sql);
            List<T> found = dao.selectList(sql, type, Map.of());
            String result = found.isEmpty() ? "ничего не найдено"
                    : "найдено " + found.size() + ": " + found.stream().map(String::valueOf).collect(Collectors.joining(", "));
            Allure.addAttachment("Результат", "text/plain", result);
            log.info("{}\n{}\n→ {}", name, sql, result);
            return found;
        });
    }
}
