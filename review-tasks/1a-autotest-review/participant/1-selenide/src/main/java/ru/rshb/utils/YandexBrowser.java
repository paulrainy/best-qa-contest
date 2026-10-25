package ru.rshb.utils;

import lombok.extern.log4j.Log4j2;
import org.openqa.selenium.SessionNotCreatedException;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeDriverService;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.manager.SeleniumManager;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Запуск тестов в Яндекс Браузере. Он собран на Chromium, поэтому им управляет обычный ChromeDriver
 * той же основной версии, что и Chromium внутри Яндекс Браузера.
 */
@Log4j2
public final class YandexBrowser {

    private static final Pattern BROWSER_VERSION = Pattern.compile("Current browser version is (\\d+)\\.");

    private static String driverPath;

    private YandexBrowser() {
    }

    /**
     * Путь к Яндекс Браузеру: из -Dyandex.binary или из стандартных мест установки.
     */
    public static Optional<Path> findBinary() {
        String fromProperty = System.getProperty("yandex.binary");
        if (fromProperty != null) {
            return Optional.of(Path.of(fromProperty));
        }
        List<Path> candidates = new ArrayList<>();
        for (String env : List.of("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)")) {
            String dir = System.getenv(env);
            if (dir != null) {
                candidates.add(Path.of(dir, "Yandex", "YandexBrowser", "Application", "browser.exe"));
            }
        }
        candidates.add(Path.of("/Applications/Yandex.app/Contents/MacOS/Yandex"));
        candidates.add(Path.of("/usr/bin/yandex-browser"));
        candidates.add(Path.of("/usr/bin/yandex-browser-stable"));
        candidates.add(Path.of("/opt/yandex/browser/yandex-browser"));
        return candidates.stream().filter(Files::isRegularFile).findFirst();
    }

    /**
     * ChromeDriver под Chromium из Яндекс Браузера: из -Dyandex.driver или через Selenium Manager.
     * Версию Chromium сообщает сам ChromeDriver, если его версия не подошла, поэтому браузер
     * при первом вызове один раз запускается на пробу.
     */
    public static synchronized String driverFor(Path binary) {
        if (driverPath != null) {
            return driverPath;
        }
        String fromProperty = System.getProperty("yandex.driver");
        if (fromProperty != null) {
            driverPath = fromProperty;
            return driverPath;
        }
        String driver = downloadDriver(null);
        Integer chromiumVersion = probe(binary, driver);
        if (chromiumVersion != null) {
            log.info("Яндекс Браузер собран на Chromium {}, скачиваем ChromeDriver этой версии", chromiumVersion);
            driver = downloadDriver(String.valueOf(chromiumVersion));
        }
        driverPath = driver;
        return driverPath;
    }

    /**
     * Пробный запуск. Возвращает версию Chromium, если драйвер не подошёл, и null, если подошёл.
     */
    private static Integer probe(Path binary, String driver) {
        ChromeOptions options = new ChromeOptions();
        options.setBinary(binary.toFile());
        options.addArguments("--headless=new");
        ChromeDriverService service = new ChromeDriverService.Builder()
                .usingDriverExecutable(new File(driver))
                .build();
        try {
            new ChromeDriver(service, options).quit();
            return null;
        } catch (SessionNotCreatedException e) {
            Matcher matcher = BROWSER_VERSION.matcher(String.valueOf(e.getMessage()));
            if (matcher.find()) {
                return Integer.parseInt(matcher.group(1));
            }
            throw e;
        }
    }

    private static String downloadDriver(String version) {
        List<String> args = new ArrayList<>(List.of("--driver", "chromedriver", "--avoid-browser-download"));
        if (version != null) {
            args.add("--driver-version");
            args.add(version);
        }
        return SeleniumManager.getInstance().getBinaryPaths(args).getDriverPath();
    }
}
