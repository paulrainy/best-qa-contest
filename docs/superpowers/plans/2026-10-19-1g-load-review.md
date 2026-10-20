# Задание 1г: ревью материалов НТ — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** собрать новое задание 1г. В нём методика НТ и 20 единиц по ней: 10 сценариев JMeter, 5 протоколов НТ, 3 дашборда Grafana и 2 SQL-скрипта. В каждой единице по 5 дефектов, всего 10 ловушек. К заданию — ключ, исправленные материалы, шаблон ответа и лист подсчёта.

**Architecture:**
- Сценарии JMeter не пишем руками в XML. Для каждого есть исходник на Python, где дефекты — ветки `if fixed`. Сборщик `build_jmx.py` выдаёт из него версию для участника и исправленную.
- Сборку проверяет настоящий JMeter 5.6.3. Скрипт на Groovy загружает план. Затем каждый элемент проходит через его GUI-класс: так видно, что GUI покажет ровно то, что мы записали.
- Протоколы пишем в Markdown, графики рисует matplotlib. `build_protocols.py` собирает из них `.docx`.
- Дашборды и SQL пишем руками, исправленные версии получаем копией с правкой.
- `build_sheets.py` учится разбирать ключ 1г. Каждое место из ключа он сверяет с материалом и падает, если материал собран из старого исходника.

**Tech Stack:**
- Python 3.12 из `review-tasks/tools/.venv`: openpyxl 3.1.5, pytest 8.3.5; новые python-docx 1.1.2 и matplotlib 3.9.2;
- Apache JMeter 5.6.3 на OpenJDK 21 (`/opt/homebrew/opt/openjdk@21`);
- Groovy из поставки JMeter;
- Grafana 10.4 в Docker — разовая проверка импорта.

**Spec:** `docs/superpowers/specs/2026-10-19-1g-load-review-design.md`

## Global Constraints

Из спецификации, дословно или близко к тексту:

- 20 единиц:
  - 01–10 — сценарии JMeter `scripts/NN-<операция>.jmx`, данные в `scripts/data/`;
  - 11–15 — протоколы `protocols/NN-<тема>.docx`;
  - 16–18 — дашборды `monitoring/NN-<тема>.json`;
  - 19–20 — `monitoring/NN-<тема>.sql`.
- В каждой единице ровно 5 дефектов, всего 100. Номер дефекта — `Д07.3`, то есть третий дефект единицы 07. В методике дефектов нет.
- Категория дефекта — `М` (расхождение с методикой) или номер пункта чек-листа отчёта НТ из `rating-tasks.md`, от 1 до 5. Ориентир — 25–35 дефектов категории `М`.
- Один и тот же приём — не больше чем в 2–3 единицах. Приём считается по конкретному дефекту, а не по группе.
- Ровно 10 ловушек `Л1`–`Л10`, ориентир по видам: 4 в сценариях, 3 в протоколах, 3 в дашбордах и SQL. В одном месте не бывает одновременно дефекта и ловушки.
- Итог: `max(0, дефекты − 2 × ловушки)`, от 0 до 100. Замечания к методике не оцениваются.
- JMeter 5.6.3. Только встроенные элементы, одна Thread Group на сценарий, 8–15 значимых элементов. Каждый дефект и каждая ловушка видны в GUI.
- Дашборды импортируются в Grafana 10.x, в каждом 6–10 панелей. Языки запросов: InfluxQL, PromQL, плагин Zabbix. SQL — диалект PostgreSQL.
- Протоколы следуют шаблону из `previous-year/yan-docs/load-test-protocol.md`, в каждом 2–4 графика. Числа фактические и согласованы между собой: закон Литтла, сумма долей, интервалы на графиках и в журнале.
- Методика фиксируется первым коммитом. После него её числа не меняются.
- Участнику сообщаем:
  - методика — единственный источник истины, ошибок в ней нет;
  - числа в протоколах — фактические;
  - в каждой единице 5 дефектов, максимум 100;
  - ловушки есть, сколько — не говорим;
  - запускать ничего не нужно.

Правила репозитория:

- Работаем в ветке `feature/1g-load-review`, на `main` не переключаемся. Каждый коммит сразу пушим.
- Коммит заканчивается строкой `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Строки ключа сортируются по единицам, внутри единицы — по месту в материале.
- Проверяющие субагенты — на Sonnet. Коммитит контролёр, а не субагент.
- Тексты для людей — по-русски, без канцелярита.
- Python запускаем только из `review-tasks/tools/.venv/bin/python`.

## Решения исполнителя (спецификация оставила их нам)

**Строки ключа.**

Дефект:

```
| Д07.3 | 07 | `Открытие вклада → POST /deposits → JSON Extractor depositId`, поле «JSON Path expressions» | М | суть | засчитываем, если |
```

Ловушка (у неё тоже есть колонка единицы):

```
| Л3 | 04 | `Вход → Once Only Controller` | попадание | почему верно |
```

Вид задания `build_sheets.py` определяет по колонке единицы в строке дефекта:

- две цифры — 1г;
- шесть — 1б;
- `TK…` — код (1а, 1д).

**Место в ключе.** Сборщик разбирает его в ключи сравнения:

| Вид | Как пишем | Ключ |
| --- | --- | --- |
| `.jmx` | путь в обратных кавычках: `` `Thread Group → Вход → POST /auth/login` `` | `jmx:<путь>` |
| `.json` | `Панель «95-й перцентиль», запрос A`, `Переменная host`, `Дашборд` | `панель:<заголовок>`, `переменная:<имя>`, `дашборд` |
| `.sql` | `строка 14`, `строки 14–16` | `строка:14`… |
| протокол | `Шапка`, `Название`, `Раздел 12.2`, `Таблица 3`, `Рисунок 2` | `шапка`, `название`, `раздел:12.2`, `таблица:3`, `рисунок:2` |

Правила для путей в `.jmx`:

- путь начинается с дочернего элемента Test Plan, сам Test Plan пишем как `` `Test Plan` ``;
- имена соседних элементов не повторяются;
- в именах нет `→` и обратных кавычек.

**Исходник сценария** — `jury/source/scripts/NN_<операция>.py`. В нём:

- константа `FILE = 'NN-<операция>'`;
- функция `plan(fixed: bool) -> jmx.El`.

Дефект — выражение вида `x if fixed else y` или условное добавление элемента. CSV для участника лежат в `participant/scripts/data/`. Если в исправленной версии CSV другой, он лежит в `jury/fixed/scripts/data/`.

**Исходник протокола** — `jury/source/protocols/NN-<тема>.md`. Графики к нему рисует `jury/source/protocols/charts.py` и кладёт в `jury/source/protocols/img/`.

Протокол устроен так:

1. До разделов:
   - строки `> …` — шапка, выравнивается вправо;
   - `# …` — название.
2. Разделы по шаблону:
   - `## 1. Сроки`;
   - `## 2. Участники`;
   - `## 3. Основание`;
   - `## 4. BIQ и наименование БИ`;
   - `## 5. Тестируемые системы`;
   - `## 6. Неизменяемые системы окружения`;
   - `## 7. Сервер`;
   - `## 8. Заключение`;
   - `## 9. Замечания`;
   - `## 10. Ограничения`;
   - `## 11. Журнал тестирования`;
   - `## 12. Результаты`: по подразделу `### 12.N <тест>` на каждый тест. В подразделе — бизнес-метрики, утилизация и вывод;
   - `## 13. Приложения`.

   Раздел может отсутствовать, если так задумано дефектом. Номера разделов идут подряд.
3. Подпись таблицы — абзац `Таблица N. …` прямо перед таблицей.
4. Рисунок — `![Рисунок N. …](img/NN-<имя>.png)`.
5. Номера таблиц и рисунков сквозные с 1.

**Устаревшие файлы.**

- `build_protocols.py` пишет в `core_properties.identifier` документа хэш исходника и картинок. `build_sheets.py` сверяет хэш и падает, если документ старше исходника.
- Для `.jmx` `build_sheets.py` собирает план в памяти и сравнивает с файлом.

**Источники данных в дашбордах.** UID фиксированные: `influxdb-nt`, `prometheus-nt`, `zabbix-nt`. Блок `__inputs` не используем.

**JMeter.** Скачиваем `apache-jmeter-5.6.3.tgz` с `archive.apache.org` в `$JMETER_HOME` во временной папке и сверяем SHA-512. В репозиторий JMeter не кладём.

## Review Focus

1. **Ключ ссылается на элемент `.jmx`, которого нет.** Элемент переименовали или перенесли в другой контроллер. Сборка ключа должна падать и называть номер дефекта.
2. **Материал старше исходника.** Исходник сценария или протокола поправили, а `.jmx` или `.docx` не пересобрали. `build_sheets.py` должен падать и называть единицу.
3. **XML, который JMeter читает молча, но показывает иначе.** Например, неверное имя свойства: JMeter его не заметит, а GUI покажет значение по умолчанию, и дефект станет невидим. Это ловит проход каждого элемента через его GUI-класс в `check_jmx.groovy`.
4. **Нумерация в протоколе.** Пропуск или повтор номера таблицы, рисунка или раздела. Рисунок без файла картинки. Строка таблицы с другим числом колонок. Сборка протокола должна падать.
5. **Битый дашборд.** Невалидный JSON, повтор `id` панели, запрос без `refId`, панель без источника данных. Всё это должно ловиться до импорта.

---

### Task 1: Методика НТ и удаление старого 1г

**Files:**
- Delete: всё содержимое `review-tasks/1g-load-review/` — `participant/report.md`, `participant/task.md`, `participant/img/`, `participant/script/`, `jury/answer-key.md`, `jury/charts.py`. Старый `charts.py` потом берём из git: `git show 5c7f806:review-tasks/1g-load-review/jury/charts.py`.
- Create: `review-tasks/1g-load-review/participant/methodology.md`

**Interfaces:**
- Produces:
  - коды операций профиля, например `ОП-01`, с долями и интенсивностью;
  - номера правил `<раздел>.<пункт>`, например `5.3`.

  Ключ, сценарии и протоколы ссылаются на них дословно.

- [ ] **Step 1: Удалить старый материал**

Run: `git rm -r review-tasks/1g-load-review/participant review-tasks/1g-load-review/jury`

- [ ] **Step 2: Написать методику**

Разделы — по спецификации, «Система и методика». Правила нумеруем. Каждое число пишем с единицей измерения и с «не больше» или «не меньше».

На эти правила будут опираться запланированные дефекты и ловушки, поэтому в методике обязательно есть:

- **Профиль.** Таблица на 8–10 операций: код, название, канал (REST, SOAP в АБС, JDBC-отчёт), доля в процентах (сумма 100), интенсивность в пиковый час в операциях в час. Под таблицей — источник статистики и дата выгрузки.
- **Модель нагрузки:**
  - как держится интенсивность: пейсинг через Flow Control Action с таймером или Precise Throughput Timer. Constant Throughput Timer на поток запрещён;
  - паузы пользователя с числами;
  - разгон: не быстрее заданного числа потоков в секунду;
  - ступени поиска максимума: шаг в процентах и длительность ступени 10 минут. Это опора ловушки;
  - верхняя граница поиска — 200 % пика, тоже опора ловушки;
  - длительность стабильности — не меньше 4 часов.
- **Критерии успеха:**
  - 95-й перцентиль по каждой операции с отдельным порогом для тяжёлого отчёта (ловушка);
  - ошибки — не больше 1 %. Ошибкой считаются ответы 5xx, включая 503, таймауты и не прошедшие проверки ответа;
  - допустимая деградация против эталона — не больше 10 % по перцентилю.
- **Данные:**
  - для каждой создающей операции — одноразовые ли данные;
  - число учётных записей менеджеров;
  - CSV — с каким режимом разделения;
  - как готовится выборка клиентов.
- **Стенд:**
  - объём критичных таблиц — не меньше 80 % от прома, таблицы перечислены;
  - заглушки ЦФТ и смежных систем отвечают с задержкой как в проме, задержки указаны;
  - вакуум и сбор статистики — до начала теста, не под нагрузкой. VACUUM FULL ночью до теста допустим (ловушка);
  - пороги генератора: CPU не больше 70 %, heap.
- **Сценарии JMeter:**
  - keep-alive включён;
  - таймауты подключения и ответа заданы, числа указаны;
  - встроенные ресурсы не загружаются;
  - проверка ответа обязательна по содержимому, а не только по коду;
  - JSR223 только на Groovy с кэшем компиляции, без `${}` в теле скрипта;
  - Beanshell, View Results Tree и Debug Sampler в нагрузочном прогоне запрещены;
  - Backend Listener в InfluxDB обязателен (ловушка);
  - хост и порт задаются через `${__P()}` (ловушка);
  - пул JDBC — не меньше числа потоков.
- **Мониторинг и артефакты:**
  - Grafana по метрикам JMeter, Zabbix по серверам;
  - PWR и логи за интервал теста;
  - время везде московское, UTC+3, и это прямо написано.
- **Требования к протоколу:**
  - разделы шаблона;
  - сравнение с эталоном по каждой операции;
  - заглушки обязательно указываются в «Ограничениях»;
  - «в пром без замечаний» нельзя писать при открытых дефектах.

- [ ] **Step 3: Самопроверка методики**

Проверить:

- доли профиля в сумме дают 100 %;
- интенсивность каждой операции равна доле от общей;
- нет двух правил, которые противоречат друг другу;
- все числа указаны с единицами;
- объём 3–5 страниц;
- названия систем, хостов, BIQ и фамилии вымышленные.

- [ ] **Step 4: Commit**

```bash
git add -A review-tasks/1g-load-review
git commit -m "feat(1г): методика НТ для нового задания, старый материал удалён"
git push
```

После этого коммита числа методики не меняются. В отчёте пользователю отметить, что методику можно посмотреть сейчас.

### Task 2: Библиотека элементов JMeter и сборщик сценариев

**Files:**
- Modify: `review-tasks/tools/requirements.txt` — добавить `python-docx==1.1.2` и `matplotlib==3.9.2`, установить: `review-tasks/tools/.venv/bin/pip install -r review-tasks/tools/requirements.txt`
- Create: `review-tasks/tools/jmx.py`
- Create: `review-tasks/tools/build_jmx.py`
- Create: `review-tasks/tools/test_jmx.py`

**Interfaces:**
- Produces в `jmx.py`:
  - `El(tag: str, gui: str, test_class: str, name: str, props: list, children: list[El] = [], enabled: bool = True, comment: str = '')`;
  - `render(root: El) -> str` — XML плана в формате JMeter 5.6.3: `<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3">`, после каждого элемента — его `<hashTree>`. Падает с `ValueError('повтор имени «X» в «Y»')`, если у соседей одинаковые имена, и с `ValueError('недопустимый символ в имени «X»')`;
  - `paths(root: El) -> dict[str, El]` — путь `A → B → C` → элемент, плюс `'Test Plan'` → корень;
  - фабрики. Каждая принимает `name`, `enabled`, `comment` и параметры элемента:
    - `test_plan`, `thread_group`;
    - `http_defaults`, `header_manager`, `cookie_manager`, `csv_data_set`, `user_variables`;
    - `http_request` (с `keep_alive`, `embedded`, `connect_timeout`, `response_timeout`, `body`, `params`);
    - `transaction`, `once_only`, `if_controller`, `loop_controller`;
    - `flow_control_action`;
    - `json_extractor`, `regex_extractor`, `response_assertion`, `json_assertion`, `duration_assertion`;
    - `constant_timer`, `uniform_random_timer`, `constant_throughput_timer`, `precise_throughput_timer`;
    - `jsr223` (тип: sampler, pre или post; `cache_key`), `beanshell_pre`;
    - `debug_sampler`;
    - `jdbc_config`, `jdbc_request`;
    - `view_results_tree`, `summary_report`, `backend_listener_influx`.

    Набор можно расширять по мере надобности в задачах 6–7.
- Produces в `build_jmx.py`:
  - `load_sources(task: Path) -> dict[str, module]` — `'07'` → модуль из `jury/source/scripts/07_*.py`;
  - `build(task: Path) -> None` — пишет `participant/scripts/<FILE>.jmx` и `jury/fixed/scripts/<FILE>.jmx`;
  - `stale(task: Path) -> list[str]` — единицы, у которых файл не совпадает с `render(plan(False))`;
  - CLI: `build_jmx.py <папка задания> [--tree NN]`. `--tree` печатает все пути плана с классом элемента: так удобно писать место в ключе.

- [ ] **Step 1: Написать падающие тесты**

`test_jmx.py`:

- `test_render_header_and_hash_trees`:
  - план «Test Plan → Thread Group → HTTP Request» разбирается `xml.etree`;
  - у корня `jmeter="5.6.3"`;
  - у каждого элемента следующий сосед — `hashTree`.
- `test_paths`: `set(paths(plan)) == {'Test Plan', 'Thread Group', 'Thread Group → Вход', 'Thread Group → Вход → POST /auth/login'}`.
- `test_duplicate_sibling_names_rejected`: два `http_request(name='GET /a')` у одного родителя → `ValueError` с текстом `повтор имени «GET /a»`.
- `test_name_with_arrow_rejected`.
- `test_disabled_element`: `enabled=False` → атрибут `enabled="false"`.
- `test_http_request_props`. Для `http_request(..., keep_alive=False, connect_timeout=5000)` в XML есть:
  - `boolProp name="HTTPSampler.use_keepalive"` = `false`;
  - `stringProp name="HTTPSampler.connect_timeout"` = `5000`.
- `test_build_writes_both_versions`. Исходник во временной папке задаёт `FILE = '01-login'` и `plan(fixed)` с `keep_alive=fixed`. После `build`:
  - `participant/scripts/01-login.jmx` содержит `use_keepalive">false`;
  - `jury/fixed/scripts/01-login.jmx` — `true`.
- `test_stale_detects_edited_file`. После `build` дописать пробел в `.jmx` → `stale(task) == ['01']`.

- [ ] **Step 2: Запустить, убедиться, что тесты падают**

Run: `cd review-tasks/tools && .venv/bin/python -m pytest test_jmx.py -q`
Expected: ошибка импорта `jmx`.

- [ ] **Step 3: Написать `jmx.py` и `build_jmx.py`**

- Имена свойств и вид XML каждого элемента берём ровно такими, как их сохраняет JMeter 5.6.3. Образец печатает `check_jmx.groovy --sample` из задачи 3. До неё ориентируемся на `bin/templates/*.jmx` из поставки.
- Отступы — два пробела, как у JMeter.
- `render` детерминирован: одинаковый вход даёт побайтно одинаковый выход.

- [ ] **Step 4: Запустить все тесты**

Run: `cd review-tasks/tools && .venv/bin/python -m pytest -q`
Expected: все тесты проходят, включая старые.

- [ ] **Step 5: Commit**

```bash
git add review-tasks/tools/jmx.py review-tasks/tools/build_jmx.py review-tasks/tools/test_jmx.py review-tasks/tools/requirements.txt
git commit -m "feat(1г): сборщик сценариев JMeter из исходников на Python"
git push
```

### Task 3: Проверка сценариев в JMeter 5.6.3

**Files:**
- Create: `review-tasks/tools/check_jmx.groovy`
- Modify: `review-tasks/tools/test_jmx.py`
- Modify: `review-tasks/tools/jmx.py` — правки по результатам проверки

**Interfaces:**
- Consumes: `render`, фабрики из задачи 2.
- Produces. Запуск:

  ```
  java -Djava.awt.headless=true -cp "$JMETER_HOME/lib/*:$JMETER_HOME/lib/ext/*" groovy.ui.GroovyMain check_jmx.groovy <файлы .jmx>
  ```

  Скрипт печатает `OK <файл>` или `FAIL <файл>: <путь>: <свойство>: наше «…», GUI «…»` и завершается с кодом 1, если есть FAIL. Режим `--sample <GuiClass>…` печатает XML элемента по умолчанию.

- [ ] **Step 1: Скачать JMeter**

```bash
export JMETER_HOME=<scratchpad>/jmeter/apache-jmeter-5.6.3
mkdir -p <scratchpad>/jmeter && cd <scratchpad>/jmeter
curl -LO https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.3.tgz
curl -LO https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.3.tgz.sha512
shasum -a 512 -c apache-jmeter-5.6.3.tgz.sha512 && tar xzf apache-jmeter-5.6.3.tgz
```

Java — `/opt/homebrew/opt/openjdk@21/bin/java`.
Expected: `apache-jmeter-5.6.3.tgz: OK`.

- [ ] **Step 2: Написать падающий тест**

`test_jmeter_round_trip` в `test_jmx.py`. Без `JMETER_HOME` он пропускается через `pytest.mark.skipif`. Тест собирает план, где есть все фабрики из задачи 2, пишет его во временный файл и запускает `check_jmx.groovy`. Ожидаем код 0 и `OK` в выводе.

Run: `cd review-tasks/tools && JMETER_HOME=… .venv/bin/python -m pytest test_jmx.py -q -k round_trip`
Expected: FAIL, пока нет `check_jmx.groovy`.

- [ ] **Step 3: Написать `check_jmx.groovy`**

1. `JMeterUtils.setJMeterHome`, `loadJMeterProperties`, `initLocale`.
2. `SaveService.loadTree(file)`. Исключение — FAIL всего файла.
3. Обход дерева. Для каждого `TestElement`:
   - создаём GUI-класс из свойства `TestElement.gui_class`;
   - `gui.configure(element)`, затем `gui.createTestElement()`;
   - сравниваем строковые значения свойств исходного элемента и копии.

   Свойства, которые GUI выставляет сам, — в списке исключений в начале скрипта, у каждого комментарий, почему.
4. `--sample` создаёт элемент через GUI-класс и печатает `SaveService.saveTree` дерева из одного элемента.

- [ ] **Step 4: Довести `jmx.py` до прохода проверки**

Каждый FAIL правим в `jmx.py`: берём XML из `--sample` того же GUI-класса. Если GUI-класс в headless не создаётся, оставляем для него только `loadTree` и записываем ruling в ledger.

Run: `cd review-tasks/tools && JMETER_HOME=… .venv/bin/python -m pytest -q`
Expected: все тесты проходят, `round_trip` не пропущен.

- [ ] **Step 5: Commit**

```bash
git add review-tasks/tools/check_jmx.groovy review-tasks/tools/jmx.py review-tasks/tools/test_jmx.py
git commit -m "feat(1г): проверка сценариев загрузкой в JMeter 5.6.3 и проходом через GUI"
git push
```

### Task 4: `build_sheets.py` понимает ключ 1г

**Files:**
- Create: `review-tasks/tools/load_places.py`
- Create: `review-tasks/tools/test_load_places.py`
- Modify: `review-tasks/tools/build_sheets.py`
- Modify: `review-tasks/tools/test_build_sheets.py`

**Interfaces:**
- Consumes: `jmx.paths`, `build_jmx.stale` (задача 2). `build_protocols.source_hash` и `build_protocols.parse` (задача 9) — до задачи 9 импортируются лениво. Протокольная часть тестов добавляется в задаче 9.
- Produces в `load_places.py`:
  - `KINDS = {'01'…'10': 'jmx', '11'…'15': 'protocol', '16'…'18': 'json', '19'…'20': 'sql'}`;
  - `place_keys(kind: str, text: str) -> set[str]`. Разбирает место по таблице из «Решений исполнителя». Если ключей нет, возвращает пустое множество;
  - `unit_files(task: Path) -> dict[str, Path]`. Ищет файлы:
    - `.jmx` — в `participant/scripts/NN-*.jmx`;
    - `.json` и `.sql` — в `participant/monitoring/NN-*`;
    - протоколы — в `jury/source/protocols/NN-*.md`.

    Если на единицу найдено два файла — `sys.exit`;
  - `targets(kind: str, path: Path) -> set[str]` — все допустимые ключи мест в файле. Для `.json` сначала вызывает `check_dashboard`;
  - `check_dashboard(path: Path) -> list[str]` — ошибки JSON:
    - не разбирается;
    - нет `title`, `uid`, `panels`, `schemaVersion`;
    - повтор `id` панели;
    - у панели нет `title`, `type`, `gridPos` или `datasource`;
    - у запроса нет `refId`.

    Строки панелей (`type: row`) и вложенные `panels` тоже проверяются;
  - `describe(kind: str, path: Path, key: str) -> str` — текст места для `--show`:
    - для `.jmx` — класс элемента и его непустые свойства;
    - для панели — запросы;
    - для SQL — текст строки;
    - для протокола — заголовок или подпись.
- Изменения `build_sheets.py`:
  - `ROW = re.compile(r'^\|\s*(Д\d{2,3}\.\d|Л\d{1,2})\s*\|(.*)\|\s*$')`;
  - `kind_of(defects) -> 'code' | 'cases' | 'load'` вместо `is_cases`;
  - `check_load(defects, traps, task) -> list[str]`. Проверяет:
    - единицы — ровно `'01'`…`'20'`;
    - номер дефекта совпадает с единицей;
    - категория из `{'М', '1', '2', '3', '4', '5'}`;
    - место разобрано и есть в материале единицы;
    - ловушка и дефект не указывают на одно место;
    - сценарии и протоколы не старше исходников;
  - `build(task, partial=False)`. С `partial` не проверяет числа единиц, дефектов и ловушек и не пишет листы. CLI-флаг `--partial`;
  - шаблон 1г: `Единица | Место | Что не так | Почему это проблема | Как исправить`;
  - лист подсчёта 1г: `№ | Единица / где | Место | Категория | Суть | Засчитываем, если… | 0 или 1`. У ловушек единица стоит в колонке B, «почему верно» — в колонке E;
  - после сборки печатается сводка: число дефектов `М` и каждого пункта 1–5.

- [ ] **Step 1: Написать падающие тесты**

`test_load_places.py`:

- `test_place_keys`, `@pytest.mark.parametrize`:
  - `('jmx', '`Вход → POST /auth/login`, поле «Path»')` → `{'jmx:Вход → POST /auth/login'}`;
  - `('json', 'Панель «95-й перцентиль», запрос A')` → `{'панель:95-й перцентиль'}`;
  - `('json', 'Переменная $host')` → `{'переменная:host'}`;
  - `('sql', 'строки 14–16')` → `{'строка:14', 'строка:15', 'строка:16'}`;
  - `('protocol', 'Раздел 12.2, Таблица 3')` → `{'раздел:12.2', 'таблица:3'}`;
  - `('protocol', 'Шапка')` → `{'шапка'}`.
- `test_targets_sql_skips_blank_lines`: в файле из трёх строк, где вторая пустая, ключи — `{'строка:1', 'строка:3'}`.
- `test_targets_dashboard`: панели внутри строки и переменные попадают в ключи.
- `test_check_dashboard_errors`, parametrize:
  - невалидный JSON → `'не разбирается'`;
  - два `id: 2` → `'повтор id 2'`;
  - запрос без `refId` → `'панель «RPS»: запрос без refId'`.

`test_build_sheets.py`. Фикстура `make_load_task(tmp_path, …)` собирает маленькое задание:

- 01–10 — `.jmx` из `jmx.render` с шестью элементами `Thread Group → S1…S6`;
- 11–15 — пока тоже `.sql` из 8 строк, а `KINDS` подменяется через `monkeypatch`: сборщика протоколов ещё нет. В задаче 9 их заменяют настоящие протоколы;
- 16–18 — `.json` с панелями `P1`…`P6`;
- 19–20 — `.sql` из 8 строк.

В ключе по 5 дефектов на единицу, на первых пяти местах, и 10 ловушек на шестом месте единиц 01–10.

Тесты:

- `test_builds_load_sheets`:
  - в шаблоне `A1 == 'Единица'` и `A2 == '01'`, `A101 == '20'`;
  - в листе подсчёта `D1 == 'Категория'`, `A2 == 'Д01.1'`, `B104 == '01'`;
  - `G116 == '=MAX(0,SUM(G2:G101)-2*SUM(G104:G113))'`.
- `test_rejects_broken_load_key`, parametrize:
  - место `` `Thread Group → S9` `` → `'Д01.1: в единице 01 нет места jmx:Thread Group → S9'`;
  - ловушка на месте дефекта → `'Л1 и дефект в одном месте: 01 jmx:Thread Group → S1'`;
  - категория `7` → `'Д01.1: категория «7»'`;
  - `Д02.1` в единице 01 → `'Д02.1: номер не совпадает с единицей 01'`;
  - место «где-то» → `'Д01.1: не понял место «где-то»'`;
  - 4 дефекта у 01 → `'01: 4 дефекта'`.
- `test_partial_skips_counts`: ключ только на единицу 01, `build(task, partial=True)` не падает и не пишет xlsx.
- `test_rejects_stale_jmx`. Фикстура с исходником в `jury/source/scripts/01_s.py`, затем правка `.jmx` → `'сценарий 01 старше исходника — запустите build_jmx.py'`.
- `test_show_prints_load_places`: `--show` печатает `Д01.1 01 jmx:Thread Group → S1:` и класс элемента.

- [ ] **Step 2: Запустить, убедиться, что новые тесты падают**

Run: `cd review-tasks/tools && .venv/bin/python -m pytest -q`
Expected: новые тесты падают, старые проходят.

- [ ] **Step 3: Написать `load_places.py` и доработать `build_sheets.py`**

Ветки для 1а, 1б и 1д не меняем, их тесты не трогаем. Обновляем docstring модуля: добавляем абзац про 1г с видами мест и флагом `--partial`.

- [ ] **Step 4: Запустить всё и пересобрать старые задания**

Run: `cd review-tasks/tools && .venv/bin/python -m pytest -q && for t in 1a-autotest-review 1b-testcase-review 1d-python-review; do .venv/bin/python build_sheets.py ../$t; done && git status --short`
Expected:
- тесты проходят;
- три задания печатают «Готово»;
- xlsx 1а, 1б и 1д не изменились по содержимому. Если `git status` показывает изменения, открыть и сравнить ячейки.

- [ ] **Step 5: Commit**

```bash
git add review-tasks/tools
git commit -m "feat(1г): build_sheets разбирает ключ 1г и сверяет места со сценариями, дашбордами и SQL"
git push
```

### Task 5: Раскладка дефектов и ловушек

**Files:**
- Create: `review-tasks/1g-load-review/jury/answer-key.md`. Это черновик: шапка, «Как считаем», категории, раскладка.

**Interfaces:**
- Consumes: правила и операции методики (задача 1).
- Produces: раскладка — по строке на единицу:

  ```
  NN | вид | операция или тема | правила методики | 5 дефектов: категория и короткое имя приёма | ловушки
  ```

  Задачи 6–8 и 10–11 пишут материал по ней.

- [ ] **Step 1: Шапка, «Как считаем», категории**

- Шапку и «Как считаем» берём из `1b-testcase-review/jury/answer-key.md`. Меняем «кейс» на «единицу», «BIQ» — на «методику».
- Добавляем:
  - дефект, видимый в двух единицах, засчитываем у любой из них, один раз;
  - место нужно только для поиска строки;
  - замечания к методике не оцениваются.
- Таблица категорий: `М` и пункты 1–5 чек-листа отчёта НТ из `rating-tasks.md`.

- [ ] **Step 2: Раскладка 20 единиц**

Ограничения:

- `М` — 25–35 дефектов. Каждый пункт 1–5 встречается не меньше 8 раз, пункт 1 ⛔ — не меньше 12.
- Сценарии 01–10 вместе покрывают все обязательные виды из спецификации: REST с корреляцией, подтверждение контролёром, одноразовые данные, тяжёлый отчёт, SOAP, JDBC, JSR223 на Groovy.
- В каждом из пяти протоколов есть хотя бы один дефект вывода (пункт 5) и хотя бы один дефект достоверности (пункт 1).
- Под раскладкой — сводка «приём → единицы». Ни у одного приёма больше 3 единиц.
- 1–3 дефекта видны в двух единицах, например ошибка сценария на графике протокола. У каждого записано, за какой единицей он числится.
- 10 ловушек, примерно 4 / 3 / 3 по видам единиц. Каждая опирается на номер правила методики или на устройство инструмента. В 12 и больше единицах ловушек нет.

- [ ] **Step 3: Проверка раскладки на Sonnet**

Субагент на Sonnet получает методику, раскладку и чек-лист отчёта НТ. Он проверяет:

- каждый дефект `М` противоречит названному правилу;
- каждая ловушка верна по методике или по устройству инструмента;
- ограничения шага 2 выполнены;
- нет дефектов, которые без запуска не увидеть.

Ответ — список замечаний. Контролёр правит раскладку. Методику не трогаем: если без правки методики не обойтись, меняем раскладку.

- [ ] **Step 4: Commit**

```bash
git add review-tasks/1g-load-review/jury/answer-key.md
git commit -m "docs(1г): раскладка дефектов и ловушек по 20 единицам"
git push
```

### Task 6: Сценарии 01–05

**Files:**
- Create: `review-tasks/1g-load-review/jury/source/scripts/01_<операция>.py` … `05_<операция>.py`
- Create: `review-tasks/1g-load-review/participant/scripts/data/*.csv`. Если в исправленной версии CSV другой, ещё и `jury/fixed/scripts/data/*.csv`
- Create (собираются): `participant/scripts/01-…jmx`…`05-…jmx`, `jury/fixed/scripts/01-…jmx`…`05-…jmx`
- Modify: `review-tasks/1g-load-review/jury/answer-key.md` — 25 строк дефектов

**Interfaces:**
- Consumes: фабрики `jmx.py`, `build_jmx.py --tree`, раскладка (задача 5), CLI `check_jmx.groovy`, `build_sheets.py --partial`.

- [ ] **Step 1: Написать исходники с дефектами и исправлениями**

- Имена элементов — как называют их нагрузочники: `POST /api/v1/clients/search`, `JSON Extractor clientId`, `Пейсинг`. Без подсказок вроде «(ошибка)».
- 8–15 значимых элементов в сценарии.
- Место ловушки из раскладки оставляем без дефекта.
- Каждый дефект — одна ветка `fixed`. Исправленная версия убирает ровно 5 дефектов и больше ничего не меняет.
- CSV — вымышленные логины и клиенты, столько строк, сколько требует методика. Если дефект «мало данных», строк меньше.

- [ ] **Step 2: Собрать и проверить в JMeter**

Run: `cd review-tasks/tools && .venv/bin/python build_jmx.py ../1g-load-review && java -Djava.awt.headless=true -cp "$JMETER_HOME/lib/*:$JMETER_HOME/lib/ext/*" groovy.ui.GroovyMain check_jmx.groovy ../1g-load-review/participant/scripts/0[1-5]-*.jmx ../1g-load-review/jury/fixed/scripts/0[1-5]-*.jmx`
Expected: 10 строк `OK`, код 0.

- [ ] **Step 3: Записать дефекты в ключ**

- Место берём из `build_jmx.py ../1g-load-review --tree NN`.
- «Засчитываем, если…» говорит, что участник должен назвать, и перечисляет допустимые формулировки.
- Строки сортируем по единице и по порядку элементов в дереве.

- [ ] **Step 4: Проверить ключ**

Run: `cd review-tasks/tools && .venv/bin/python build_sheets.py ../1g-load-review --partial && .venv/bin/python build_sheets.py ../1g-load-review --show`
Expected:
- ошибок нет;
- `--show` для каждой строки печатает элемент, в котором виден дефект.

Сверить глазами: дефект виден в напечатанных свойствах, в исправленной версии его нет (`diff` двух `.jmx`).

- [ ] **Step 5: Commit**

```bash
git add review-tasks/1g-load-review
git commit -m "feat(1г): сценарии JMeter 01–05 с ключом и исправленными версиями"
git push
```

### Task 7: Сценарии 06–10

Как задача 6, с единицами 06–10. Проверка — `0[6-9]-*.jmx 10-*.jmx`, ожидаем 10 строк `OK`.

Коммит: `feat(1г): сценарии JMeter 06–10 с ключом и исправленными версиями`.

Дополнительная проверка: сводка «приём → единицы» в раскладке обновлена по сценариям 01–10, ни у одного приёма больше 3 единиц.

### Task 8: Дашборды 16–18 и SQL 19–20

**Files:**
- Create: `participant/monitoring/16-…json`, `17-…json`, `18-…json`, `19-…sql`, `20-…sql`
- Create: `jury/fixed/monitoring/` — те же пять файлов, исправленные
- Modify: `jury/answer-key.md` — 25 строк дефектов

**Interfaces:**
- Consumes: `load_places.check_dashboard`, `build_sheets.py --partial` и `--show`, раскладка.

- [ ] **Step 1: Написать дашборды**

- 16 — метрики JMeter в InfluxDB, InfluxQL, источник `influxdb-nt`.
- 17 — метрики JMeter в Prometheus, PromQL, источник `prometheus-nt`.
- 18 — утилизация серверов из Zabbix, плагин `alexanderzobnin-zabbix-datasource`, источник `zabbix-nt`.

В каждом:

- 6–10 панелей;
- переменные;
- `schemaVersion` как у Grafana 10.4;
- JSON сокращён до полей, которые влияют на вид и запросы.

Измерения и поля InfluxDB — как пишет Backend Listener JMeter: `jmeter`, теги `transaction`, `statut`, поля `count`, `avg`, `pct95.0`.

- [ ] **Step 2: Написать SQL**

- 19 — подготовка стенда: вакуум, объём критичных таблиц против прома, проверка записи пишущего сервиса.
- 20 — сбор артефактов и подготовка данных: PWR за интервал, логи через `pg_read_file`, выборка клиентов в CSV.

Пишем комментариями, как это делает инженер. Номера строк не должны сдвигаться после записи ключа.

- [ ] **Step 3: Исправленные версии**

Скопировать в `jury/fixed/monitoring/` и исправить ровно 5 дефектов в каждом файле.

Run: `diff -r participant/monitoring jury/fixed/monitoring`
Expected: каждое различие — дефект из раскладки.

- [ ] **Step 4: Ключ и проверка**

25 строк дефектов. Место — по таблице «Решения исполнителя».

Run: `cd review-tasks/tools && .venv/bin/python build_sheets.py ../1g-load-review --partial && .venv/bin/python build_sheets.py ../1g-load-review --show`
Expected: ошибок нет, `--show` печатает запросы панелей и строки SQL с дефектами.

- [ ] **Step 5: Импорт в Grafana**

Если Docker не запускается за 2 минуты, этот шаг пропускаем и пишем ruling в ledger. Проверка JSON уже прошла в шаге 4.

```bash
open -a Docker   # ждём, пока `docker info` ответит
docker run -d --rm --name grafana-1g -p 3300:3000 grafana/grafana:10.4.2
```

Через API (`admin:admin`):

1. Создать источники данных с uid `influxdb-nt` (InfluxQL) и `prometheus-nt`.
2. Импортировать 16 и 17 через `POST /api/dashboards/db` с `overwrite: true`. Затем `GET /api/dashboards/uid/<uid>`: число панелей совпадает с файлом.
3. Импортировать 18 без плагина. Ожидаем `status: success`.
4. Повторить для `jury/fixed/monitoring/`.
5. `docker stop grafana-1g`.

Expected: все шесть импортов успешны, число панелей совпадает.

- [ ] **Step 6: Commit**

```bash
git add review-tasks/1g-load-review
git commit -m "feat(1г): дашборды Grafana 16–18 и SQL 19–20 с ключом и исправленными версиями"
git push
```

### Task 9: Сборщик протоколов

**Files:**
- Create: `review-tasks/tools/build_protocols.py`
- Create: `review-tasks/tools/test_build_protocols.py`
- Create: `review-tasks/1g-load-review/jury/source/protocols/charts.py` — общие функции стиля, без данных протоколов
- Modify: `review-tasks/tools/test_build_sheets.py` — протокольная часть фикстуры `make_load_task` и тест устаревшего протокола

**Interfaces:**
- Produces в `build_protocols.py`:
  - `Protocol(header: list[str], title: str, blocks: list)`, где блок — заголовок, абзац, список, таблица с подписью или рисунок с подписью;
  - `parse(path: Path) -> Protocol`. Падает `sys.exit('<файл>: …')`, если:
    - номера разделов, таблиц или рисунков идут не подряд;
    - у рисунка нет файла картинки;
    - в строке таблицы не то число колонок;
    - таблица без подписи;
  - `places(protocol) -> dict[str, str]` — ключ места (`раздел:12.2`, `таблица:3`, `рисунок:2`, `шапка`, `название`) → текст заголовка или подписи. Им пользуется `load_places.targets`;
  - `source_hash(path: Path) -> str` — sha256 от текста `.md` и байтов всех картинок, на которые он ссылается, первые 16 знаков;
  - `write(protocol, md_path: Path, out: Path) -> None`. Оформление:
    - Times New Roman 12;
    - заголовки — стилями `Heading 1/2/3`;
    - таблицы — стиль `Table Grid`, шапка жирная;
    - картинки шириной 16 см, подписи курсивом;
    - шапка выровнена вправо;
    - `**жирный**` внутри абзацев и ячеек;
    - `core_properties.identifier = source_hash(md_path)`;
  - CLI: `build_protocols.py <папка задания>` — все `jury/source/protocols/NN-*.md` → `participant/protocols/NN-*.docx`.
- Produces в `charts.py`:
  - `style()` — светлая тема в духе Grafana: белый фон, светлая сетка, Arial, кириллица;
  - `timeseries(ax, t, series: dict[str, array], unit: str)` — линии и легенда-таблица с Avg и Max под графиком;
  - `minutes(start: str, values) -> list[datetime]` — ось времени HH:MM.

- [ ] **Step 1: Написать падающие тесты**

`test_build_protocols.py` на маленьком исходнике (шапка, название, разделы 1, 2, 2.1, две таблицы, один рисунок; картинку создаёт matplotlib в фикстуре):

- `test_parse_places`: `set(places(p)) == {'шапка', 'название', 'раздел:1', 'раздел:2', 'раздел:2.1', 'таблица:1', 'таблица:2', 'рисунок:1'}`.
- `test_rejects`, parametrize:
  - вторая таблица подписана `Таблица 3` → `'Таблица 3 после Таблица 1'`;
  - картинки нет → `'нет файла img/x.png'`;
  - строка таблицы на 4 колонки при шапке на 5 → `'Таблица 1: строка 2 — 4 колонки, нужно 5'`;
  - раздел `## 3.` после `## 1.` → `'раздел 3 после 1'`.
- `test_write_docx`. Собранный документ, открытый python-docx:
  - есть абзац `2.1 …` со стилем `Heading 3`;
  - `len(doc.tables) == 2`;
  - `len(doc.inline_shapes) == 1`;
  - `doc.core_properties.identifier == source_hash(md)`;
  - у абзаца шапки выравнивание `RIGHT`;
  - `**жирный**` даёт run с `bold`.
- `test_hash_changes_with_image`: перезапись картинки меняет `source_hash`.

`test_build_sheets.py`:

- фикстура `make_load_task` получает настоящие протоколы 11–15, подмена `KINDS` убирается;
- `test_rejects_stale_protocol`: правка `.md` после сборки → `'протокол 11 старше исходника — запустите build_protocols.py'`.

- [ ] **Step 2: Запустить, убедиться, что тесты падают**

Run: `cd review-tasks/tools && .venv/bin/python -m pytest -q`
Expected: новые тесты падают, остальные проходят.

- [ ] **Step 3: Написать `build_protocols.py` и `charts.py`**

Разбор — построчный, по синтаксису из «Решений исполнителя». В `load_places.targets` для протоколов вызываем `build_protocols.places(build_protocols.parse(path))`.

- [ ] **Step 4: Запустить все тесты**

Run: `cd review-tasks/tools && .venv/bin/python -m pytest -q`
Expected: все тесты проходят.

- [ ] **Step 5: Commit**

```bash
git add review-tasks/tools review-tasks/1g-load-review/jury/source/protocols/charts.py
git commit -m "feat(1г): сборщик протоколов НТ в docx и стиль графиков"
git push
```

### Task 10: Протоколы 11–13

**Files:**
- Create: `jury/source/protocols/11-…md`, `12-…md`, `13-…md`
- Modify: `jury/source/protocols/charts.py` — данные и функции графиков для 11–13, команда `charts.py NN` и `charts.py --tables NN`
- Create (собираются): `jury/source/protocols/img/11-*.png`…, `participant/protocols/11-…docx`…`13-…docx`
- Modify: `jury/answer-key.md`:
  - 15 строк дефектов;
  - в разделе «Протоколы: правильный вывод» — абзац на протокол;
  - в разделе «Самопроверка чисел» — расчёт по каждому протоколу.

**Interfaces:**
- Consumes: `charts.style`, `charts.timeseries`, `build_protocols` CLI, раскладка.

Темы по спецификации: 11 — поиск максимума, 12 — стабильность, 13 — сравнение с эталоном.

- [ ] **Step 1: Задать числа**

В `charts.py` на каждый протокол — блок констант:

- ступени или интервалы;
- поданная интенсивность по операциям;
- времена отклика;
- ошибки по кодам;
- утилизация.

Ряды строятся по ним с шумом и фиксированным `seed`. Для закрытой модели число потоков, интенсивность и время отклика связаны законом Литтла. `charts.py --tables NN` печатает таблицы средних по ступеням в Markdown, их и вставляем в протокол.

Старые числа из `git show 5c7f806:review-tasks/1g-load-review/jury/charts.py` можно брать за основу.

- [ ] **Step 2: Написать протоколы**

- Разделы по шаблону.
- Вымышленные ФИО, версии и контуры.
- Таблицы — из `--tables`.
- 2–4 рисунка.
- Пять дефектов на протокол по раскладке: в подготовке и проведении теста, в выводах и в недостающем. В числах дефектов нет.
- Место ловушки оставляем верным.

- [ ] **Step 3: Собрать**

Run: `cd review-tasks/1g-load-review/jury/source/protocols && ../../../../tools/.venv/bin/python charts.py 11 12 13 && cd ../../../../tools && .venv/bin/python build_protocols.py ../1g-load-review`
Expected: картинки и три `.docx` собраны без ошибок.

- [ ] **Step 4: Ключ, правильный вывод и самопроверка**

- Строки дефектов: место — раздел, таблица или рисунок.
- Правильный вывод: что должно стоять в заключении и почему.
- Самопроверка: для каждой ступени закон Литтла `потоки ≈ интенсивность × (время отклика + пауза)` сходится в пределах 5 %. Сумма долей — 100 %. Интервалы журнала совпадают с осью времени на рисунках.

Run: `cd review-tasks/tools && .venv/bin/python build_sheets.py ../1g-load-review --partial && .venv/bin/python build_sheets.py ../1g-load-review --show`
Expected: ошибок нет.

- [ ] **Step 5: Посмотреть документы глазами**

Сконвертировать в PDF через LibreOffice, если он есть (`soffice --headless --convert-to pdf`). Если нет — открыть картинки и прочитать текст документа через python-docx. Проверить:

- кириллица на графиках читается;
- подписи и легенды не обрезаны;
- таблицы помещаются по ширине.

- [ ] **Step 6: Commit**

```bash
git add review-tasks/1g-load-review
git commit -m "feat(1г): протоколы НТ 11–13 с ключом, правильными выводами и самопроверкой чисел"
git push
```

### Task 11: Протоколы 14–15

Как задача 10, с протоколами 14 (контрольный прогон после исправления) и 15 (интеграция с АБС на заглушке).

Коммит: `feat(1г): протоколы НТ 14–15 с ключом, правильными выводами и самопроверкой чисел`.

Дополнительная проверка: сводка «приём → единицы» обновлена по всем 20 единицам, ни у одного приёма больше 3 единиц. Число дефектов `М` — 25–35.

### Task 12: Ловушки, листы, `task.md`

**Files:**
- Modify: `jury/answer-key.md`:
  - раздел «Ловушки»: `| № | Единица | Где | Как выглядит замечание-попадание | Почему верно |`;
  - «Верные замечания вне ключа»;
  - «Что проверить перед запуском»;
  - раскладку свернуть в сводку категорий и приёмов.
- Create: `participant/task.md`
- Create (собираются): `participant/answer-template.xlsx`, `jury/scoring-sheet.xlsx`

**Interfaces:**
- Consumes: CLI `build_jmx.py`, `build_protocols.py`, `build_sheets.py`.

- [ ] **Step 1: Ловушки в ключ**

10 строк по раскладке, сортируем по единице и месту. «Почему верно» ссылается на номер правила методики или на устройство инструмента.

- [ ] **Step 2: `task.md`**

По образцу `1b-testcase-review/participant/task.md`. Разделы:

- что сделать;
- что в архиве и чем открывать;
- как обозначать место — четыре вида из «Решений исполнителя», с примерами;
- формат ответа — колонки шаблона;
- как считаются баллы.

Пять фактов из «Что знает участник» — дословно.

- [ ] **Step 3: Собрать всё**

Run: `cd review-tasks/tools && .venv/bin/python build_jmx.py ../1g-load-review && .venv/bin/python build_protocols.py ../1g-load-review && .venv/bin/python build_sheets.py ../1g-load-review && .venv/bin/python build_sheets.py ../1g-load-review --show > <workspace>/show.txt && .venv/bin/python -m pytest -q`
Expected:
- `build_sheets.py` печатает «Готово» и сводку категорий;
- в `show.txt` 110 блоков, каждый показывает место с дефектом или ловушкой;
- тесты проходят.

- [ ] **Step 4: Проверить все `.jmx` в JMeter**

Run: `java -Djava.awt.headless=true -cp "$JMETER_HOME/lib/*:$JMETER_HOME/lib/ext/*" groovy.ui.GroovyMain review-tasks/tools/check_jmx.groovy review-tasks/1g-load-review/participant/scripts/*.jmx review-tasks/1g-load-review/jury/fixed/scripts/*.jmx`
Expected: 20 строк `OK`.

- [ ] **Step 5: Commit**

```bash
git add review-tasks/1g-load-review
git commit -m "feat(1г): ловушки, шаблон ответа, лист подсчёта и условие задания"
git push
```

### Task 13: Проверка вслепую

**Files:**
- Modify по итогам: исходники, ключ, материалы. Методику — только если найдена её ошибка. Тогда это отдельный коммит, и все опирающиеся на неё строки ключа нужно перепроверить.

- [ ] **Step 1: Решение на Sonnet**

Субагент на Sonnet получает только `participant/`. Ему говорим: «Ты участник конкурса, реши задание по `task.md`». `.docx` он читает через python-docx, `.jmx` — как XML.

Ответ — таблица с колонками шаблона в Markdown, в файл `<workspace>/blind.md`.

- [ ] **Step 2: Сверка с ключом**

- Замечание вне ключа — исправить материал или внести в «Верные замечания вне ключа».
- Попадание в ловушку — убедиться, что она однозначно верна, иначе переделать.
- Ненайденный дефект — убедиться, что он находим по материалу без запуска.

Итог прогона (найдено X из 100, ловушек Y) записать в «Что проверить перед запуском».

- [ ] **Step 3: Проверка исправленных материалов на Sonnet**

Отдельный субагент на Sonnet получает методику, чек-лист отчёта НТ, `jury/fixed/` и правильные выводы по протоколам из ключа. Задача — найти дефекты. Каждое замечание контролёр исправляет в исходнике или отклоняет с причиной.

- [ ] **Step 4: Пересобрать и проверить**

Команды шагов 3 и 4 задачи 12.
Expected: то же.

- [ ] **Step 5: Commit**

```bash
git add review-tasks/1g-load-review
git commit -m "fix(1г): правки по решению вслепую и проверке исправленных материалов"
git push
```

### Task 14: README и `rating-tasks.md`

**Files:**
- Modify: `review-tasks/README.md`:
  - раздел «1г. Ревью отчёта и скрипта НТ — для нагрузочников» (строка 65) заменить итоговым описанием по образцу 1б;
  - рекомендацию в строке 127 обновить;
  - в «Как устроены папки заданий» добавить `scripts/`, `protocols/`, `monitoring/`, `methodology.md`.
- Modify: `rating-tasks.md:98` — уточнить, что для нагрузочников без доступных материалов — новый 1г.

- [ ] **Step 1: Раздел 1г в README**

Описать:

- что сдаёт участник и что в архиве;
- шкалу 0–100;
- как проверяет жюри и сколько занимает проверка;
- как пересобрать материалы: команды из шага 3 задачи 12 и проверку JMeter из шага 4;
- что живые люди решают задание перед запуском.

- [ ] **Step 2: Обновить `rating-tasks.md`**

- [ ] **Step 3: Commit**

```bash
git add review-tasks/README.md rating-tasks.md
git commit -m "docs(1г): описание нового задания в README и rating-tasks"
git push
```
