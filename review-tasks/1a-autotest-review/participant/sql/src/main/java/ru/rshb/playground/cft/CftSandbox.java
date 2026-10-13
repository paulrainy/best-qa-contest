package ru.rshb.playground.cft;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.h2.tools.Server;

import java.io.IOException;
import java.net.Socket;
import java.sql.SQLException;
import java.util.EnumMap;
import java.util.Map;

/**
 * Песочница: базы стендов (H2 в памяти), TCP-сервер, через который к ним подключаются тесты и консоль, и API ЦФТ.
 * Данные заполняются заново при каждом запуске.
 */
public final class CftSandbox {

    private static final Logger log = LogManager.getLogger(CftSandbox.class);

    public static final int API_PORT = Integer.getInteger("cft.port", 18090);
    public static final int DB_PORT = Integer.getInteger("cft.db.port", 19092);
    public static final int CONSOLE_PORT = Integer.getInteger("cft.console.port", 18082);

    private static boolean started;

    private CftSandbox() {
    }

    public static void main(String[] args) throws Exception {
        start();
        Server.createWebServer("-webPort", String.valueOf(CONSOLE_PORT)).start();
        log.info("Песочница запущена. API ЦФТ: http://localhost:{}/cft/<стенд>/api/", API_PORT);
        log.info("Консоль базы данных: http://localhost:{}", CONSOLE_PORT);
        for (Stand stand : Stand.values()) {
            log.info("  {} ({}): JDBC URL {}, пользователь sa, пароль пустой", stand, stand.getTypeDb(), stand.jdbcUrl());
        }
        log.info("Пароль всех пользователей ЦФТ: {}. Остановить — Ctrl+C", Stand.PASSWORD);
        Thread.currentThread().join();
    }

    /**
     * Запускает песочницу, если она ещё не запущена отдельно через mvn exec:java.
     */
    public static synchronized void startIfNotRunning() {
        if (started || portBusy(API_PORT)) {
            return;
        }
        try {
            start();
            log.info("Песочница запущена вместе с тестами, стенд {}", Stand.current());
        } catch (Exception e) {
            throw new IllegalStateException("Не удалось запустить песочницу: " + e.getMessage(), e);
        }
    }

    private static void start() throws SQLException, IOException {
        Map<Stand, CftDb> databases = new EnumMap<>(Stand.class);
        for (Stand stand : Stand.values()) {
            CftDb db = new CftDb(stand);
            CftSeed.fill(db);
            databases.put(stand, db);
        }
        Server.createTcpServer("-tcpPort", String.valueOf(DB_PORT), "-tcpDaemon").start();
        new CftStubServer(databases).start(API_PORT);
        started = true;
    }

    private static boolean portBusy(int port) {
        try (Socket ignored = new Socket("localhost", port)) {
            return true;
        } catch (IOException e) {
            return false;
        }
    }
}
