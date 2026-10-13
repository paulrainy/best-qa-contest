package ru.rshb.playground.cft;

import enums.TypeDb;

import java.util.Map;

/**
 * Стенды ЦФТ в песочнице. У каждого своя база в памяти: Oracle-стенды — H2 в режиме Oracle,
 * PostgreSQL-стенд — H2 в режиме PostgreSQL.
 * <p>
 * ID записей справочника состояний генерируются последовательностью при заполнении справочника, поэтому
 * на разных стендах они разные. PGRF1RT перенесён на PostgreSQL с копии RTEST, ID у них совпадают.
 */
public enum Stand {

    RTEST(TypeDb.ORACLE, Map.of("WAIT_CONF", 2047892L, "WORK", 2047893L, "OPEN", 2047895L, "CLOSE", 2047897L)),
    INTEST(TypeDb.ORACLE, Map.of("WAIT_CONF", 3105511L, "WORK", 3105512L, "OPEN", 3105514L, "CLOSE", 3105516L)),
    PGRF1RT(TypeDb.POSTGRE, Map.of("WAIT_CONF", 2047892L, "WORK", 2047893L, "OPEN", 2047895L, "CLOSE", 2047897L));

    /** Пароль всех пользователей песочницы. */
    public static final String PASSWORD = "Cft#Playground";

    private final TypeDb typeDb;
    private final Map<String, Long> statusIds;

    Stand(TypeDb typeDb, Map<String, Long> statusIds) {
        this.typeDb = typeDb;
        this.statusIds = statusIds;
    }

    /**
     * Стенд, на котором идут тесты: -Dstand=..., по умолчанию RTEST.
     */
    public static Stand current() {
        String name = System.getProperty("stand", "RTEST").trim().toUpperCase();
        try {
            return valueOf(name);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Неизвестный стенд " + name + ". Есть: RTEST, INTEST, PGRF1RT");
        }
    }

    public TypeDb getTypeDb() {
        return typeDb;
    }

    Map<String, Long> statusIds() {
        return statusIds;
    }

    private String mode() {
        return typeDb == TypeDb.ORACLE ? "Oracle" : "PostgreSQL";
    }

    /** Адрес базы для тестов и консоли: через TCP-сервер песочницы. */
    public String jdbcUrl() {
        return "jdbc:h2:tcp://localhost:%d/mem:%s;MODE=%s".formatted(CftSandbox.DB_PORT, name(), mode());
    }

    /** Адрес базы внутри процесса песочницы. */
    String localJdbcUrl() {
        return "jdbc:h2:mem:%s;MODE=%s;DB_CLOSE_DELAY=-1".formatted(name(), mode());
    }
}
