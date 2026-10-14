"""Браузер для UI-тестов — установленный на компьютере: Яндекс Браузер, если его нет — Google Chrome.
BROWSER=chrome или BROWSER=yandex — только этот браузер, BROWSER_PATH — свой путь к браузеру."""
import logging
import os
from pathlib import Path

log = logging.getLogger('browser')


def _windows(*parts):
    return [Path(os.environ[env], *parts) for env in ('LOCALAPPDATA', 'ProgramFiles', 'ProgramFiles(x86)')
            if os.environ.get(env)]


YANDEX = _windows('Yandex', 'YandexBrowser', 'Application', 'browser.exe') + [
    Path('/Applications/Yandex.app/Contents/MacOS/Yandex'),
    Path('/usr/bin/yandex-browser'), Path('/usr/bin/yandex-browser-stable'), Path('/opt/yandex/browser/yandex-browser'),
]
CHROME = _windows('Google', 'Chrome', 'Application', 'chrome.exe') + [
    Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
    Path('/usr/bin/google-chrome'), Path('/usr/bin/google-chrome-stable'), Path('/opt/google/chrome/chrome'),
]


def find_browser() -> str:
    if os.getenv('BROWSER_PATH'):
        return os.environ['BROWSER_PATH']
    choice = os.getenv('BROWSER', 'auto').lower()
    candidates = (YANDEX if choice != 'chrome' else []) + (CHROME if choice != 'yandex' else [])
    for path in candidates:
        if path.is_file():
            log.info('Браузер для тестов: %s', path)
            return str(path)
    names = {'yandex': 'Яндекс Браузер не найден', 'chrome': 'Google Chrome не найден'}
    raise RuntimeError(names.get(choice, 'Не найден ни Яндекс Браузер, ни Google Chrome')
                       + '. Укажите путь к браузеру в переменной окружения BROWSER_PATH')
