package ru.rshb.playground;

import lombok.extern.log4j.Log4j2;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * Браузер, установленный на компьютере. Playwright управляет любым браузером на Chromium, если указать путь к нему,
 * поэтому отдельно скачивать браузер или драйвер не нужно.
 * <p>
 * По умолчанию — Яндекс Браузер, если он установлен (на ВДИ компании запуск Chrome запрещён), иначе Google Chrome.
 * -Dbrowser=chrome — только Chrome, -Dbrowser=yandex — только Яндекс Браузер, -Dbrowser.path=... — свой путь.
 */
@Log4j2
public final class LocalBrowser {

    private static Path found;

    private LocalBrowser() {
    }

    public static synchronized Path find() {
        if (found != null) {
            return found;
        }
        String path = System.getProperty("browser.path");
        if (path != null) {
            found = Path.of(path);
            return found;
        }
        String browser = System.getProperty("browser", "auto");
        Optional<Path> yandex = browser.equals("chrome") ? Optional.empty() : firstExisting(yandexCandidates());
        Optional<Path> chrome = browser.equals("yandex") ? Optional.empty() : firstExisting(chromeCandidates());
        found = yandex.or(() -> chrome).orElseThrow(() -> new IllegalStateException(switch (browser) {
            case "yandex" -> "Яндекс Браузер не найден. Укажите путь к нему: -Dbrowser.path=...";
            case "chrome" -> "Google Chrome не найден. Укажите путь к нему: -Dbrowser.path=...";
            default -> "Не найден ни Яндекс Браузер, ни Google Chrome. Установите один из них "
                    + "или укажите путь к браузеру: -Dbrowser.path=...";
        }));
        log.info("Браузер для тестов: {}", found);
        return found;
    }

    private static List<Path> yandexCandidates() {
        List<Path> candidates = new ArrayList<>();
        for (String dir : windowsDirs()) {
            candidates.add(Path.of(dir, "Yandex", "YandexBrowser", "Application", "browser.exe"));
        }
        candidates.add(Path.of("/Applications/Yandex.app/Contents/MacOS/Yandex"));
        candidates.add(Path.of("/usr/bin/yandex-browser"));
        candidates.add(Path.of("/usr/bin/yandex-browser-stable"));
        candidates.add(Path.of("/opt/yandex/browser/yandex-browser"));
        return candidates;
    }

    private static List<Path> chromeCandidates() {
        List<Path> candidates = new ArrayList<>();
        for (String dir : windowsDirs()) {
            candidates.add(Path.of(dir, "Google", "Chrome", "Application", "chrome.exe"));
        }
        candidates.add(Path.of("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"));
        candidates.add(Path.of("/usr/bin/google-chrome"));
        candidates.add(Path.of("/usr/bin/google-chrome-stable"));
        candidates.add(Path.of("/opt/google/chrome/chrome"));
        return candidates;
    }

    private static List<String> windowsDirs() {
        List<String> dirs = new ArrayList<>();
        for (String env : List.of("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)")) {
            String dir = System.getenv(env);
            if (dir != null) {
                dirs.add(dir);
            }
        }
        return dirs;
    }

    private static Optional<Path> firstExisting(List<Path> candidates) {
        return candidates.stream().filter(Files::isRegularFile).findFirst();
    }
}
