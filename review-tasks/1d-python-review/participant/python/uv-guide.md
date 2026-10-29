# Запуск Python-проекта через uv

Все команды выполняйте в папке `python/`, рядом с `pyproject.toml`. На Windows подойдёт PowerShell, cmd или терминал IDE. Активация окружения и системные команды `python` и `pip` не нужны.

## Подготовка

Проверьте, что uv доступен:

```bash
uv --version
```

Если команда не найдена, используйте установленный на ВДИ `uv.exe` по полному пути или добавьте папку с ним в `PATH`. Если uv ещё не установлен, способы установки и готовые исполняемые файлы есть в [официальной инструкции](https://docs.astral.sh/uv/getting-started/installation/). После установки откройте новый терминал.

Создайте окружение и установите зависимости:

```bash
uv sync
```

Окружение появится в `.venv`. Файл `.python-version` выбирает Python 3.11, а `uv.lock` фиксирует версии всех зависимостей. Если подходящего Python нет, uv скачает его; для этого нужен доступ к источнику загрузки Python. Уже установленный Python 3.11 можно указать явно: `uv sync --python "C:\путь\к\python.exe"`.

## Запуск тестов

```bash
uv run pytest
```

При следующих запусках повторять установку не нужно: `uv run` использует `.venv` и при необходимости синхронизирует зависимости. Можно сразу выполнить `uv run pytest` даже при первом запуске.

Зависимости и настройки pytest находятся в `pyproject.toml`. Сохраняйте `uv.lock` и `.python-version` вместе с проектом — они нужны и в архиве участника. При подготовке окружений организаторами команда `uv sync --locked` проверит, что lock-файл соответствует конфигурации, и установит зависимости без его обновления.

| Что нужно | Команда |
| --- | --- |
| Один тест | `uv run pytest tests/1-api/test_900303_refill.py` |
| Только API и БД | `uv run pytest tests/1-api` |
| Только Kafka | `uv run pytest tests/2-kafka` |
| UI с видимым браузером | `uv run pytest tests/3-ui --headed` |
| Параллельно в 4 потока | `uv run pytest -n 4` |
| Показать запросы API и БД | `uv run pytest -o log_cli=true` |

Для UI нужен установленный Яндекс Браузер или Google Chrome. Браузеры через `playwright install` скачивать не требуется.

Переменные окружения в PowerShell задавайте перед запуском, например:

```powershell
$env:BROWSER = "chrome"
uv run pytest tests/3-ui --headed
```

В cmd используйте `set BROWSER=chrome`, в Git Bash, macOS и Linux — `BROWSER=chrome uv run pytest tests/3-ui --headed`.

## Подключение к IDE

Сначала выполните команды подготовки. Затем выберите существующий интерпретатор `.venv\Scripts\python.exe` на Windows или `.venv/bin/python` на macOS и Linux:

- **PyCharm:** Settings → Project → Python Interpreter → Add Interpreter → Add Local Interpreter → Existing.
- **VS Code:** команда `Python: Select Interpreter` → Enter interpreter path.

После этого тесты можно запускать кнопками IDE; повторно создавать окружение в ней не нужно.

## Песочница и результаты

При запуске тестов песочница поднимается сама. Чтобы работать с ней вручную, выполните в отдельном терминале:

```bash
uv run python -m sandbox
```

API — http://localhost:18300/api/v1/, кабинет — http://localhost:18300/cabinet/. Пока песочница запущена, тесты используют её; данные сохраняются между прогонами. Остановка — Ctrl+C; при новом запуске база создаётся заново.

| Учётная запись песочницы | Логин | Пароль |
| --- | --- | --- |
| Бэк-офис | `bo_operator1` | `Oper1#Playground` |
| Клиенты | `ivanova_ma`, `petrov_sv`, `smirnov_ap`, `kuznetsova_ei`, `volkov_dn`, `inv_client_lock` | `Client#Playground` |

БД песочницы — `build/invest.db` (SQLite). Поручения через API исполняются примерно через 1,5–2,5 секунды; клиенты стенда каждую секунду создают свои пополнения. Сообщения внешних систем песочница обрабатывает каждые полсекунды.

Результат виден в консоли. Данные Allure — в `build/allure-results`: при установленном Allure отчёт открывается командой `allure serve build/allure-results`. Скриншоты и трейсы упавших UI-тестов — в `build/test-results`; `trace.zip` можно открыть на https://trace.playwright.dev.

## Если не запускается

| Проблема | Что сделать |
| --- | --- |
| Не скачивается Python | Укажите уже установленный Python 3.11: `uv sync --python "C:\путь\к\python.exe"`. Для загрузки через uv нужен доступ к источнику дистрибутива Python. |
| Нет доступа к PyPI | Укажите зеркало организации в переменной `UV_DEFAULT_INDEX` перед `uv sync` и последующими запусками. В PowerShell: `$env:UV_DEFAULT_INDEX = "https://адрес-зеркала/simple"`. Адрес уточните у администратора; uv не читает настройки `pip.ini`. Смена индекса может обновить `uv.lock`. |
| `No module named pytest` или не найдена команда `pytest` | Проверьте текущую папку и повторите `uv sync`. |
| Не найден браузер | Задайте в PowerShell `$env:BROWSER_PATH = "C:\путь\к\browser.exe"` и повторите запуск. |
| Ошибка драйвера Playwright или `node` | Если встроенный Node.js блокируется, укажите установленный: `$env:PLAYWRIGHT_NODEJS_PATH = "C:\Program Files\nodejs\node.exe"`. |
| Ошибка соединения со стендом | Проверьте, не занят ли порт 18300. Для другого порта задайте `$env:INVEST_SANDBOX_PORT = "18301"` и повторите запуск. |
| В Git Bash искажён русский текст | Выполните `export PYTHONUTF8=1` и повторите запуск. |

На Windows не требуется запускать `Activate.ps1` или менять политику выполнения PowerShell. О командах проекта подробнее — в [документации uv](https://docs.astral.sh/uv/guides/projects/).
