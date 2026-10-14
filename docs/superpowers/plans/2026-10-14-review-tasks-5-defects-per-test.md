# Задания 1а и 1д: по 5 дефектов в каждом тесте — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** переделать задания 1а и 1д так, чтобы в каждом из 40 тестов было ровно 5 дефектов в файле теста, в общих файлах дефектов не было, ловушек было ровно 10 на задание, а проверка сводилась к сверке двух Excel-таблиц.

**Architecture:** дорабатываем существующие тесты в песочницах (путь A из спецификации). Дефекты из общих файлов переезжают в тесты, общие файлы исправляются. Для каждой части: правим общий код → вносим дефекты в тесты → пишем исправленные версии в `jury/fixed/` → прогоняем «как есть» и «с исправлениями» → собираем раздел ключа. Excel-шаблон ответа и лист подсчёта строятся скриптом из ключа, скрипт же проверяет инварианты (5 дефектов на тест, 10 ловушек, нет строк «дефект + ловушка»).

**Tech Stack:** Java 17 + Maven (Selenide/TestNG, H2, Playwright/JUnit 5), Python 3.10+ (pytest, PyHamcrest, pytest-playwright, SQLite), openpyxl для Excel.

**Spec:** `docs/superpowers/specs/2026-10-14-review-tasks-5-defects-per-test-design.md`

## Global Constraints

Из спецификации, дословно:

- В каждом задании 20 тестов. Тест — это файл теста и один кейс Test IT.
- TK900218 становится вторым набором данных в TK900118, как два набора в TK900109.
- В каждом тесте ровно 5 дефектов, и все они в файле этого теста.
- В общих файлах дефектов нет.
- Ловушек ровно 10 на задание. Ловушка может лежать где угодно, в том числе в общем файле. Распределение неравномерное: в большинстве тестов ловушек нет, где-то одна, в одном месте две-три подряд.
- В одной строке не бывает одновременно дефекта и ловушки.
- Один и тот же приём (например, `Thread.sleep`) встречается не больше чем в 2–3 тестах.
- Дефект может проявляться в другом тесте: строка в TK A, симптом в TK B. Такой дефект записан у TK A и считается один раз, но засчитывается, если участник написал замечание у A или у B.
- +1 за дефект, найденный с верной причиной. Место обязательно.
- −2 за каждую ловушку, в которую попал участник. Штраф снимается с общей суммы, каждая ловушка штрафуется один раз.
- Итог: `max(0, дефекты − 2 × ловушки)`, от 0 до 100.
- Нумерация дефектов по тесту: `Д102.3` — третий дефект TK900102. Ловушки — `Л1`–`Л10` в каждом задании.
- Принцип прежний: заглушки работают правильно, большинство дефектных тестов зелёные, часть дефектов видна при запуске — это описано в ключе.
- Песочница по-прежнему ничего не пишет в окружение участника.
- 1г не трогаем.

Правила репозитория и сессии:

- Работаем в ветке `feature/1a-1d-scoring-per-test`, на `main` не переключаемся. Каждый коммит сразу пушим.
- Коммит заканчивается строкой `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Строки ключа сортируются по месту в материале: по тестам, внутри теста — по строкам.
- Тексты для людей — по-русски, без канцелярита. `task.md` правим только в разделах, которые меняет спецификация.

Как читать таблицы дефектов ниже:

- Метки `Д101.а`–`Д101.д` — рабочие. Окончательные номера `Д101.1`–`Д101.5` ставятся по порядку строк в готовом файле.
- Пункт: `1⛔`–`5` — пункты чек-листа, `SQL`, `Kafka`, `PW` (Playwright), `pytest` — технические категории.
- «Было» — номер дефекта в текущем ключе, если дефект переезжает или остаётся.

## Review Focus

Пять ситуаций, которые спецификация подразумевает, но шаги задач сами по себе не проверяют:

1. **Два дефекта на соседних строках или в одной конструкции.** Проверяющий не должен сомневаться, какой из двух засчитать. Ожидание: у каждой такой пары в колонке «Засчитываем, если…» назван признак, который отличает одно замечание от другого. Проверяется в шаге «Самопроверка ключа» задач 4 и 8.
2. **Номера строк в ключе разъехались с кодом** после последней правки теста. Ожидание: каждая ссылка `Файл:строка` указывает на строку с дефектом. Скрипт `build_sheets.py --show` печатает процитированные строки, их сверяют глазами (задачи 4 и 8).
3. **Ловушка и дефект в одной строке.** Ожидание: такого нет. Скрипт падает, если у дефекта и ловушки совпадает `Файл:строка` (задача 4, тест скрипта).
4. **Прогон на ВДИ** (Windows, Яндекс Браузер, Maven 3.6.3) ведёт себя иначе, чем на Mac. Ожидание: ни один новый дефект не завязан на ОС, путь с `C:\` или часовой пояс, кроме уже описанного Д9 в 1д. Проверяется прогоном пользователя (задачи 4 и 8, последний шаг).
5. **Excel-файлы в старом Excel или LibreOffice.** Ожидание: только формулы `SUM` и `MAX`, проверка ввода 0/1, без макросов; файлы открываются и пересчитываются. Проверяется чтением файла обратно в тесте скрипта (задача 4).

## Файлы

Создаются:

- `review-tasks/tools/build_sheets.py` — собирает Excel-шаблон ответа и лист подсчёта из ключа, проверяет инварианты ключа.
- `review-tasks/tools/test_build_sheets.py` — тесты скрипта на маленьком ключе-образце.
- `review-tasks/tools/requirements.txt` — `openpyxl==3.1.5`.
- `review-tasks/1a-autotest-review/participant/answer-template.xlsx`, `review-tasks/1a-autotest-review/jury/scoring-sheet.xlsx`.
- `review-tasks/1d-python-review/participant/answer-template.xlsx`, `review-tasks/1d-python-review/jury/scoring-sheet.xlsx`.
- `review-tasks/1a-autotest-review/jury/fixed/{selenide,sql,playwright}/…` — исправленные версии изменённых файлов тестов, пути как в песочнице.
- `review-tasks/1d-python-review/jury/fixed/python/…` — то же для 1д.
- `review-tasks/1a-autotest-review/participant/selenide/src/test/resources/web_users_test3.yaml` — нужен дефекту Д105.

Меняются:

- Тесты 1а: `participant/selenide/src/test/java/ru/rshb/tests/cards/card_block/TK9001{01..10}Test.java`, `participant/sql/src/test/java/tests/PRODUCTS/R2_DEPOSIT/rko_fl/*Test.java`, `participant/playwright/src/test/java/ru/rshb/pw/cards/TK9001{11..15}Test.java`.
- Общий код 1а: `CardsHelper.java`, `web_users.yaml`, `CriteriaR2Deposit.java`, `CriteriaClPriv.java`, `OpenNewDepositPageHelper.java`, `CardPage.java`. Удаляется `DepositDbSteps.java`.
- Тесты 1д: `tests/api/**/test_9003{01..10}_*.py`, `tests/kafka/test_9003{11..15}_*.py`, `tests/ui/test_9003{16..20}_*.py`.
- Общий код 1д: `tests/conftest.py`, `invest/steps/clients.py`, `invest/db/invest_db.py`, `invest/kafka/kafka_steps.py`, `tests/ui/conftest.py`, `invest/pages/cabinet.py`.
- Ключи `1a-autotest-review/jury/answer-key.md`, `1d-python-review/jury/answer-key.md` — переписываются целиком по новой структуре.
- `task.md`: `participant/selenide/`, `participant/sql/`, `participant/playwright/` в 1а и `participant/python/` в 1д.
- `review-tasks/README.md`, `rating-tasks.md`.
- `.gitignore` — `review-tasks/tools/.venv/`.

## Отклонения от спецификации, о которых надо сказать пользователю

- **Д5 из 1д** (голый `assert` в модуле, который не тест) и **ДК1** (ошибка топика проглатывается в шагах) не переезжают: в файле теста pytest переписывает `assert`, а свой клиент Kafka тест не пишет. Общий код исправляется, вместо них в тестах новые дефекты.
- **ДП1 из 1д** (одна фикстура клиента на сессию) не переезжает: межтестовый эффект давала общая фикстура, в файле теста его не повторить. Вместо него новый дефект.
- **Из ловушек 1а** остаются Л1, Л3, Л4, Л9, Л10, ЛС1, ЛС2, ЛП1, ЛП3, ЛП4. **Из ловушек 1д** остаются Л2, Л3, Л5, Л7, Л9, Л10, ЛК1, ЛК5, ЛП3, ЛП5. Код снятых ловушек остаётся (он корректный), в ключ они не входят. Замечание к такому месту — «вне ключа»: баллов не даёт и не штрафуется.
- **Новые ожидаемые результаты в кейсах Test IT** — только там, где дефекту нужен материал. Список — в задачах по частям.

Всё это надо показать пользователю в итоговом сообщении после задачи 4 (по 1а) и задачи 8 (по 1д).

---

### Task 1: 1а Selenide — общий хелпер и 10 тестов

**Files:**
- Modify: `review-tasks/1a-autotest-review/participant/selenide/src/test/java/ru/rshb/tests/cards/card_block/CardsHelper.java`
- Modify: `…/card_block/TK900101Test.java` … `TK900110Test.java`
- Modify: `…/selenide/src/test/resources/web_users.yaml`
- Create: `…/selenide/src/test/resources/web_users_test3.yaml`
- Create: `review-tasks/1a-autotest-review/jury/fixed/selenide/src/test/java/ru/rshb/tests/cards/card_block/TK9001{01..10}Test.java`
- Create (черновик раздела ключа): `review-tasks/1a-autotest-review/jury/draft-selenide.md` — удаляется в задаче 4 после сборки ключа

**Interfaces:**
- Produces: `CardsHelper.unblockCard(String message, CardProfilePage cardPage, String supervisorLogin, String supervisorPassword)`; `CardsHelper.checkCardStatus` сравнивает текст статуса; в `CardsHelper` нет статических полей `blockedCardClient`, `blockedCardNumber` и метода `checkReissuedCards`; статические поля `TK900101Test.blockedCardClient`, `TK900101Test.blockedCardNumber` читает TK900103.

- [ ] **Step 1: Исправить `CardsHelper.java`**

Убрать из хелпера все дефекты (Д1, Д4, Д6, Д7, Д10, Д18 текущего ключа). Ловушки Л1 (ожидания по 30 секунд, строки `blockCard` и `unblockCard`) и Л4 (`catch (AssertionError e)` с пробросом в `checkPinChangeUnavailable`) не трогать.

```java
// удалить строки 37–39 (статические поля) и 44–45 (SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD)

@Step("{message}")
public CardProfilePage openCard(String message, NewEfrClientSearchPage searchPage,
                                String passportSeries, String passportNumber, String cardNumber) {
    log.info("=---> {}", message);

    searchPage.passportSeriesAndNumberInput(passportSeries, passportNumber);
    searchPage.clickSearchButton();
    $x("//div[@data-id='productProfile']").shouldBe(visible, Duration.ofSeconds(30));
    allureReport.messageWithConsole("Открыт продуктовый профиль клиента");

    String lastDigits = cardNumber.substring(cardNumber.length() - 4);
    $x("//a[contains(text(),'" + lastDigits + "')]").click();
    $x("//div[@data-id='cardProfile']").as("Карточка карты").shouldBe(visible);
    allureReport.messageWithConsole("Открыта карта *%s".formatted(lastDigits));

    return new CardProfilePage();
}

@Step("{message}")
public void checkCardStatus(String message, CardProfilePage cardPage, String expectedStatus) {
    log.info("=---> {}", message);

    $x(cardPage.cardStatusXpath).as("Статус карты").shouldHave(exactText(expectedStatus));
    allureReport.messageWithConsole("Статус карты: '%s'".formatted(expectedStatus));
}

@Step("{message}")
public void unblockCard(String message, CardProfilePage cardPage, String supervisorLogin, String supervisorPassword) {
    log.info("=---> {}", message);

    $x(cardPage.unblockButtonXpath).click();
    $x(cardPage.supervisorLoginXpath).setValue(supervisorLogin);
    $x(cardPage.supervisorPasswordXpath).setValue(supervisorPassword);
    $x(cardPage.confirmButtonXpath).click();

    $x(cardPage.notificationXpath).shouldHave(text("Карта разблокирована"), Duration.ofSeconds(30));
    allureReport.messageWithConsole("Отображается сообщение 'Карта разблокирована'");
}

@Step("{message}")
public void checkHistoryRecord(String message, CardProfilePage cardPage, String operation) {
    log.info("=---> {}", message);

    $x(cardPage.historyTabXpath).click();
    $$x(cardPage.historyRowXpath + "[contains(., '" + operation + "')]")
            .as("Записи '%s' в истории".formatted(operation))
            .shouldHave(sizeGreaterThan(0));
    allureReport.messageWithConsole("В истории есть запись '%s'".formatted(operation));
}

// метод checkReissuedCards удалить — он переезжает в TK900104Test приватным методом
```

Импорты: добавить `exactText`, `sizeGreaterThan`; убрать `ElementsCollection`, `not`, `size`, `assertThat`, если больше не используются. В `web_users.yaml` добавить:

```yaml
rf_card_sup1:           # Старший менеджер (подтверждает разблокировку)
  login: rf_card_sup1
  password: Kart0chka#2026
```

Перед этим найти в `selenide/src/main/java/ru/rshb/playground/efr/EfrStore.java` логин и пароль старшего менеджера, которые принимает заглушка, и подставить их, если они отличаются от `Kart0chka#2026`.

Создать `web_users_test3.yaml` — копию `web_users.yaml` с заголовком `# Учётные записи ролей на test3`.

- [ ] **Step 2: Внести дефекты в TK900101–TK900105**

| Тест | Метка | Пункт | Было | Что вносим | Исправление в `jury/fixed` |
| --- | --- | --- | --- | --- | --- |
| 101 | а | 3 | — | `allureReport.messageWithConsole("Подготовка: вход в ЕФР. %s / %s".formatted(webUser.getLogin(), webUser.getPassword()));` — пароль роли уходит в лог и Allure | Писать только роль |
| 101 | б | 1⛔ | — | Шаг 1: убрать `checkCardStatus(... "Активна")`, оставить комментарий `// новая карта всегда активна` | `checkCardStatus("Шаг 1: …", cardPage, "Активна")` |
| 101 | в | 1⛔ | Д1 | Шаг 2: вместо `checkCardStatus` — `$x(cardPage.cardStatusXpath).shouldBe(visible);` и `allureReport.messageWithConsole("Шаг 2: Статус карты 'Заблокирована'");` | `checkCardStatus(... "Заблокирована")` |
| 101 | г | 5 | — | Шаг 2: вместо `checkButtonDisplayed` — `$x("//button[normalize-space()='Разблокировать']").as("Кнопка 'Заблокировать'").shouldBe(visible);` — подпись от другой кнопки | `checkButtonDisplayed(... "Разблокировать")` |
| 101 | д | 5 | Д10 | Шаг 3: проверка истории прямо в тесте внутри `try { … } catch (Throwable e) { log.warn("История операций не прогрузилась: {}", e.getMessage()); }`, `$$x(...).size()` и `assertThat(records).isGreaterThan(0)` как в старом хелпере | `checkHistoryRecord(...)` |
| 101 | — | — | Д7 | В классе объявить `static EfrClient blockedCardClient; static String blockedCardNumber; // Для TK900103` и после шага 2 присвоить. Это часть Д103.б, отдельного дефекта у 101 нет | Полей и присваивания нет |
| 102 | а | 5 | — | `@TestitStatus(autoTestId = "1900101", autoTestExternalId = "@900101")` — скопировано из TK900101, результат уйдёт в чужой кейс | `1900102`, `@900102` |
| 102 | б | 4 | Д8 | Без изменений: паспорт `4510 123456`, карта `2200 7001 2345 6789` зашиты | Создать клиента и карту через API |
| 102 | в | 2 | Д3 | Без изменений: `Thread.sleep(5000)` | `$x(cardPage.successNotificationXpath).shouldHave(text("Лимит изменён"))` |
| 102 | г | 5 | Д9 | Без изменений: `assertTrue(...equals("50 000"))` | `$x(...).as("Поле 'Снятие наличных, в месяц'").shouldHave(exactValue("50 000"))` |
| 102 | д | 1⛔ | Д2 | Без изменений: скриншот вместо проверки сообщения | Проверка сообщения (см. в) |
| 103 | а | 3 | Д5 | Без изменений: `open("http://localhost:18080/efr/")` | `stand.get(...)`, `open(stand.getNewEfrApplicationUrl())` |
| 103 | б | 4 | Д7 | Шаг 1 берёт `TK900101Test.blockedCardClient` и `TK900101Test.blockedCardNumber`. Отдельно — NPE | Клиент, карта и блокировка через API, как в TK900105 |
| 103 | в | 1⛔ | — | Шаг 1: статус «Заблокирована» не проверяется (как сейчас) | `checkCardStatus(... "Заблокирована")` |
| 103 | г | 3 | Д6 | Шаг 2: `unblockCard("…", cardPage, "rf_card_sup1", "Kart0chka#2026");` | `WebUser supervisor = new WebUser(); supervisor.get("rf_card_sup1", "web_users.yaml");` и его логин и пароль |
| 103 | д | 2 | — | После `unblockCard`: `while (!$x(cardPage.cardStatusXpath).getText().equals("Активна")) { Thread.sleep(500); }  // ждём, пока процессинг применит разблокировку` — самодельное ожидание без таймаута, тест зависнет | Удалить: `checkCardStatus` ждёт сам |
| 104 | а | 3 | — | Первой строкой подготовки: `System.setProperty("env.name", "test2");  // на test3 перевыпуск не настроен`. Свойство не возвращается — следующие тесты тоже идут на test2 (засчитываем и как пункт 4) | Удалить |
| 104 | б | 2 | Д14 | Без изменений: `Selenide.sleep(10000)` | Удалить |
| 104 | в | 1⛔ | Д13 | Сообщение «Заявка на перевыпуск создана» не проверяется | `$x(cardPage.notificationXpath).as("Сообщение").shouldHave(exactText("Заявка на перевыпуск создана"))` |
| 104 | г | 1⛔ | Д13 | Статус старой карты «Закрыта» не проверяется | `waitForCardStatusInProfile("Шаг 3: Старая карта в статусе 'Закрыта'", lastDigits(cardNumber), "Закрыта")` |
| 104 | д | 5 | Д18 | Приватный `checkReissuedCards` в тесте, без `@Step` и без записи в лог (код из старого хелпера) | Добавить `@Step("Проверить, что в профиле две карты")` |
| 105 | а | 5 | — | После `selenideSetUp()`: `Configuration.screenshots = false;  // скриншоты здесь не нужны` — глобально и не возвращается, у следующих упавших тестов нет скриншота (засчитываем и как пункт 4) | Удалить |
| 105 | б | 3 | — | `webUser.get("rf_card_mng1", "web_users_test3.yaml");` — файл учёток конкретного стенда | `web_users.yaml` |
| 105 | в | 2 | Д4 | После `openCard`: `Thread.sleep(3000);  // подождать прогрузку карточки` | Удалить |
| 105 | г | 1⛔ | — | Шаг 1: `$x(cardPage.cardStatusXpath).as("Статус карты").shouldNot(text("Активна"));` — пройдёт при любом другом статусе | `shouldHave(exactText("Заблокирована"))` |
| 105 | д | 4 | — | `@Override public void closeBrowser() { }  // браузер не закрываю — так быстрее` — следующий тест в потоке получает открытый браузер с сессией | Удалить переопределение |

Шаг 2 TK900105 по-прежнему через `checkPinChangeUnavailable` — там ловушка Л4.

- [ ] **Step 3: Внести дефекты в TK900106–TK900110**

| Тест | Метка | Пункт | Было | Что вносим | Исправление в `jury/fixed` |
| --- | --- | --- | --- | --- | --- |
| 106 | а | 4 | — | `@Test(groups = {"@900106"}, dependsOnGroups = {"@900102"})  // сначала убедиться, что лимит вообще меняется` | Убрать `dependsOnGroups` |
| 106 | б | 1⛔ | Д11 | Шаг 1: значение по умолчанию 100 000 не проверяется | `$x(cardPage.cashLimitInputXpath).as(...).shouldHave(exactValue(DEFAULT_CASH_LIMIT))` перед вводом |
| 106 | в | 1⛔ | Д11 | Шаг 2: текст ошибки «Превышен максимальный лимит 500 000 ₽» не проверяется | `$x(cardPage.notificationXpath).as("Сообщение об ошибке").shouldHave(exactText("Превышен максимальный лимит 500 000 ₽"))` |
| 106 | г | 1⛔ | Д12 | Без изменений: `shouldNotBe(visible)` сразу после «Сохранить» | После проверки ошибки (в): `$x(cardPage.successNotificationXpath).shouldNotBe(visible)` |
| 106 | д | 5 | — | Шаг 3: `assertEquals(DEFAULT_CASH_LIMIT, $x(cardPage.cashLimitInputXpath).getValue(), "Лимит после обновления");` — TestNG ждёт `(actual, expected)`, в сообщении «ожидалось» и «получено» перепутаны | `shouldHave(exactValue(DEFAULT_CASH_LIMIT))` |
| 107 | а | 3 | Д15 | Без изменений: `stand.get("test2", …)` | Стенд из окружения |
| 107 | б | 4 | Д16 | Без изменений: `Configuration.timeout = 60000` | Удалить |
| 107 | в | 1⛔ | — | Номер карты убрать из словаря и проверить отдельно: `assertThat($x(cardPage.requisiteCardNumberXpath).getText()).startsWith("•••• ");` — последние 4 цифры не сверяются | `shouldHave(exactText("•••• " + lastDigits))` |
| 107 | г | 1⛔ | — | Счёт убрать из словаря с комментарием `// счёт на test2 приходит пустым, проверим после починки стенда` | Счёт в словаре |
| 107 | д | 5 | Д17 | Без изменений: цикл без `.as(...)` | Словарь «название поля → (xpath, значение)», `$x(xpath).as(name).shouldHave(exactText(value))` |
| 108 | а | 5 | — | `allureReport.replaceTestMethodName("Разблокировка карты");` — имя TK900103 | «Разблокировка без подтверждения старшего менеджера» |
| 108 | б | 1⛔ | Д20 | Шаг 2: ошибка «Требуется подтверждение старшего менеджера» не проверяется | `$x(cardPage.notificationXpath).shouldHave(exactText("Требуется подтверждение старшего менеджера"))` |
| 108 | в | 1⛔ | Д19 | Без изменений: `fail` внутри `try`, `catch (Throwable e)` | Убрать `try`; после проверки ошибки — `shouldNotHave(text("Карта разблокирована"))` |
| 108 | г | 2 | — | Перед «Отмена»: `Selenide.sleep(2000);  // окно ошибки закрывается с анимацией` | Удалить |
| 108 | д | 1⛔ | Д20 | Шаг 3: закрытие окна и статус «Заблокирована» не проверяются, только клик и запись в лог | `$x("//div[@role='dialog']").as("Окно подтверждения").shouldNotBe(visible)`, `checkCardStatus(... "Заблокирована")` |
| 109 | а | 2 | — | В начале теста: `Configuration.pollingInterval = 5000;  // реже опрашивать стенд` — каждая проверка, которой надо подождать, ждёт кратно 5 секундам; не возвращается (засчитываем и как пункт 4) | Удалить |
| 109 | б | 4 | Д22 | Без изменений: клиент и карта в `@BeforeClass`, общие на обе границы | Готовить в начале теста |
| 109 | в | 1⛔ | Д21 | Без изменений: `text("изменён")` | `exactText("Лимит изменён")` |
| 109 | г | 1⛔ | — | Отдельной строкой: `.shouldHave(value(expectedValue))` — `value()` ищет подстроку, `value("0")` пройдёт для «300 000» | `exactValue(expectedValue)` |
| 109 | д | 1⛔ | — | Новый шаг 3: `refresh(); openTab("Шаг 3: Обновить карточку и открыть вкладку 'Лимиты'", "Лимиты");` — и всё, значение после обновления не проверяется | `$x(cardPage.onlineLimitInputXpath).shouldHave(exactValue(expectedValue))` |
| 110 | а | 3 | Д23 | Без изменений: личные логин и пароль | `webUser.get("rf_card_mng1", "web_users.yaml")` |
| 110 | б | 1⛔ | — | Шаг 1: `$x(cardPage.cardStatusXpath).as("Статус карты").shouldBe(visible);` — текст не сверяется | `shouldHave(exactText("Активна"))` |
| 110 | в | 5 | — | Шаг 2: проверка статуса после отмены с подписью `.as("Окно блокировки")` — скопирована со строки выше | `.as("Статус карты")` |
| 110 | г | 2 | — | Шаг 3: вместо `$$x(cardPage.historyRowXpath).shouldHave(sizeGreaterThan(0))` — `Thread.sleep(1500);  // история грузится полторы секунды` | Вернуть ожидание `sizeGreaterThan(0)` |
| 110 | д | 1⛔ | — | Шаг 3: `"[contains(., 'Блокирование карты')]"` — в истории пишется «Блокировка карты», проверка отсутствия проходит всегда | `'Блокировка карты'` |

Ловушки, которые остаются в Selenide-части: Л1 (`CardsHelper`, ожидания 30 секунд), Л4 (`CardsHelper`, `catch (AssertionError)` с пробросом), Л3 (TK900106, `"500001"`), Л9 (TK900109, DataProvider), Л10 (TK900110, только строка `$x(cardPage.blockDialogXpath).shouldNotBe(visible)` — ожидание закрытия открытого окна). Строки с ловушками не трогать.

Thread.sleep в части: 102, 105, 110. `Selenide.sleep`: 104, 108. Глобальный `Configuration`: 105, 107, 109.

- [ ] **Step 4: Обновить кейс TK-900109 в `participant/selenide/task.md`**

Добавить в таблицу кейса строку:

```markdown
| 3 | Обновить карточку карты, открыть вкладку «Лимиты» | В поле «Покупки в интернете, в месяц» — введённое значение |
```

- [ ] **Step 5: Прогнать как есть**

Run: `cd review-tasks/1a-autotest-review/participant/selenide && mvn -q test -Dselenide.headless=true 2>&1 | tail -40`

Expected: компиляция без ошибок. Большинство тестов зелёные. Записать фактический итог (сколько прошло, какие упали и с какой ошибкой, длительности TK900108 и TK900109) — он идёт в раздел «Что видно в песочнице». Ожидаемо видны: Д103.б (`mvn test -Dtest=TK900103Test` — NPE), Д106.а (`mvn test -Dtest=TK900106Test` — TestNG сообщает о зависимости от отсутствующей группы), Д107.б (TK900108 в полном прогоне дольше, чем отдельно), Д105.д (может уронить TK900106: браузер с сессией не закрыт). Если Д105.д ломает следующий тест не всегда, записать это как «нестабильно» и проверить три прогона.

Отдельно прогнать:

```bash
mvn -q test -Dselenide.headless=true -Dtest=TK900103Test 2>&1 | grep -E "Tests run|NullPointer"
mvn -q test -Dselenide.headless=true -Dtest=TK900106Test 2>&1 | grep -E "Tests run|depends on|nonexistent"
mvn -q test -Dselenide.headless=true -Dtest=TK900105Test+TK900106Test 2>&1 | grep -E "Tests run|FAIL"
```

- [ ] **Step 6: Написать исправленные версии в `jury/fixed/selenide/`**

Скопировать 10 тестов в `review-tasks/1a-autotest-review/jury/fixed/selenide/src/test/java/ru/rshb/tests/cards/card_block/` и в каждом применить колонку «Исправление» из таблиц шагов 2–3. TK900103 в исправленной версии готовит заблокированную карту сам:

```java
EfrClient efrClient = efrApiProcessing.clientCreateWithTelephone(stand, webUser);
String cardNumber = efrApiProcessing.issueDebitCard(stand, webUser, efrClient.getClientId());
efrApiProcessing.blockCard(stand, webUser, cardNumber, "Утеря");
```

- [ ] **Step 7: Прогнать исправленные версии**

```bash
SCR=/private/tmp/claude-501/-Users-paul-Documents-work-best-qa-contest/23501aa8-6b9f-4038-aaae-44488e6418c8/scratchpad
SRC=review-tasks/1a-autotest-review/participant/selenide
rm -rf $SCR/selenide-fixed && rsync -a --exclude target --exclude .m2 --exclude .selenium $SRC/ $SCR/selenide-fixed/
cp -R review-tasks/1a-autotest-review/jury/fixed/selenide/. $SCR/selenide-fixed/
cd $SCR/selenide-fixed && mvn -q test -Dselenide.headless=true -Dmaven.repo.local=$OLDPWD/$SRC/.m2/repository 2>&1 | tail -20
```

Expected: `Tests run: 11, Failures: 0, Errors: 0, Skipped: 0`. Если что-то упало — чинить исправленную версию, а не тест участника, пока не станет понятно, что падение вызвано заложенным дефектом, который забыли исправить.

- [ ] **Step 8: Черновик раздела ключа**

В `jury/draft-selenide.md` для каждого теста таблица «№ | Тест | Файл:строки | Суть одной фразой | Засчитываем, если…» с окончательными номерами `Д101.1`… по порядку строк. Номера строк — по готовым файлам (`grep -n`). Для Д103.2 указать оба места (`TK900103Test.java:…` и `TK900101Test.java:…`), для Д104.1, Д105.1, Д107.2, Д109.1 — тест, где проявляется. Таблица ловушек — по старым формулировкам Л1, Л3, Л4, Л9, Л10 с новыми номерами строк. Раздел «Что видно в песочнице» — по фактическим результатам шага 5.

- [ ] **Step 9: Commit**

```bash
git add review-tasks/1a-autotest-review/participant/selenide review-tasks/1a-autotest-review/jury/fixed/selenide review-tasks/1a-autotest-review/jury/draft-selenide.md
git commit -m "feat: 1а Selenide — по 5 дефектов в каждом тесте, хелпер без дефектов

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 2: 1а Java + SQL — 5 тестов, TK900218 внутри TK900118

**Files:**
- Modify: `review-tasks/1a-autotest-review/participant/sql/src/test/java/model_cft/model/PRODUCTS/r2_deposit/CriteriaR2Deposit.java`
- Modify: `…/sql/src/test/java/model_cft/model/CLIENTS/clPriv/CriteriaClPriv.java`
- Delete: `…/sql/src/test/java/tests/PRODUCTS/R2_DEPOSIT/rko_fl/DepositDbSteps.java`
- Modify: `…/rko_fl/OpenCurrentAccountTest.java`, `CashDepositToCurrentAccountTest.java`, `ArrestOnCurrentAccountTest.java`, `CloseCurrentAccountTest.java`, `OpenAccountWithExpiredDocTest.java`
- Modify: `…/sql/src/main/java/CFT/PRODUCT/R2_DEPOSIT/pages/operation_openNewDeposit/OpenNewDepositPageHelper.java` (добавить `getErrorText()`)
- Modify при необходимости: `…/sql/src/main/java/ru/rshb/playground/cft/CftSeed.java` (данные для Д116.б, Д117.в, Д120.б, исправленного Д119)
- Modify: `…/sql/task.md` (кейс TK-900118)
- Create: `review-tasks/1a-autotest-review/jury/fixed/sql/src/test/java/tests/PRODUCTS/R2_DEPOSIT/rko_fl/*Test.java`
- Create: `review-tasks/1a-autotest-review/jury/draft-sql.md`

**Interfaces:**
- Consumes: ничего из задачи 1.
- Produces: `CriteriaR2Deposit.withStatusEqualTo` фильтрует по `C_CODE` справочника; `withoutActiveCard` через `NOT EXISTS`; в `CriteriaClPriv` нет `withoutExecutoryProcess` и `withFatca`; `OpenNewDepositPageHelper.getErrorText(): String`.

- [ ] **Step 1: Исправить общий код**

`CriteriaR2Deposit.java`: удалить `STATUS_IDS` и комментарий над ним; `withStatusEqualTo` и `withoutActiveCard` переписать, ловушку ЛС1 (`withoutActiveHold`, LEFT JOIN с условием в `ON`) не трогать.

```java
public CriteriaR2Deposit withStatusEqualTo(ComStatusPrd status) {

    queryBuilder
            .join("INNER JOIN Z#COM_STATUS_PRD st ON st.ID = d.C_COM_STATUS")
            .where("st.C_CODE = '%s'".formatted(status.getCode()));
    addParameter("Состояние", status.getDescription());

    return this;
}

public CriteriaR2Deposit withoutActiveCard() {

    queryBuilder.where("""
            NOT EXISTS (SELECT 1
                        FROM Z#R2_IP_CARDS ic
                        WHERE ic.C_DEPOSIT = d.ID
                          AND ic.C_STATE = 'ACTIVE')""");
    addParameter("Действующие карты", "нет");

    return this;
}
```

Если у `ComStatusPrd` метод кода называется иначе, взять его из `ComStatusPrd.java`. `CriteriaClPriv.java`: удалить методы `withoutExecutoryProcess` и `withFatca` целиком. `OpenNewDepositPageHelper.java`: добавить рядом с `checkErrorTextEqualTo` метод `public String getErrorText()`, который возвращает тот же текст, что сравнивает `checkErrorTextEqualTo`. Удалить `DepositDbSteps.java`.

- [ ] **Step 2: Внести дефекты**

| Тест | Метка | Пункт | Было | Что вносим | Исправление в `jury/fixed` |
| --- | --- | --- | --- | --- | --- |
| 116 | а | 1⛔ | — | Убрать `.hasAccountStartWith(BalanceAccount.$40817)` | Вернуть |
| 116 | б | 3 | — | Цикл `for (Branch branch : List.of(Branch.<код, где на RTEST есть клиенты с FATCA>))  // на RTEST клиенты с FATCA только в этом филиале` вместо `getProductBranchesWithCheckOperDayEqualCurrDay()`. Код взять из `Branch.java` и `CftSeed` | `getProductBranchesWithCheckOperDayEqualCurrDay()` |
| 116 | в | SQL | ДС2 | В сетапе: `clPrivCriteria.getQueryBuilder().where("cp.ID NOT IN (SELECT ep.C_CLIENT FROM Z#EXECUTORY_PROCESS ep)");  // в CriteriaClPriv такого метода нет` | `NOT EXISTS (SELECT 1 FROM Z#EXECUTORY_PROCESS ep WHERE ep.C_CLIENT = cp.ID)` |
| 116 | г | SQL | ДС10 | В сетапе: фрагмент FATCA с `OR` без скобок, как в старом `withFatca` | Скобки вокруг `f.C_DATE_END IS NULL OR f.C_DATE_END >= …` |
| 116 | д | 5 | ДС7 | Без изменений: после цикла проверяется только `clPriv` | `AssertionsUtil.assertThat(user).objectExist();` |
| 117 | а | 1⛔ | — | Итоговая проверка остатка: `Assertions.assertThat(deposit.update().getBalance()).isGreaterThan(balanceBefore);` — пройдёт при любом увеличении | `hasBalanceEqualTo(balanceBefore.add(AMOUNT))` |
| 117 | б | 2 | — | Перед поиском операции: `TimeUnit.SECONDS.sleep(5);  // операция появляется в БД не сразу` | Удалить |
| 117 | в | SQL | ДС4 | Приватный метод `getLastFactOper(Dto_Deposit)` в тесте: `SELECT fo.* FROM Z#R2_FACT_OPER fo WHERE fo.C_DEPOSIT = :depositId FETCH FIRST 1 ROWS ONLY`, с `@Step` | `ORDER BY fo.ID DESC`, фильтр по сумме `AMOUNT` и дате операционного дня |
| 117 | г | 3 | ДС1 | В сетапе вместо `.withStatusEqualTo(ComStatusPrd.$WORK)`: `.getQueryBuilder().where("d.C_COM_STATUS = 2047893");  // «Работает»` — ID справочника с RTEST. Метод `getQueryBuilder()` возвращает билдер, цепочку продолжить отдельной переменной | `.withStatusEqualTo(ComStatusPrd.$WORK)` |
| 117 | д | 3 | — | Кассир: `cashier = new CriteriaUser(); cashier.getQueryBuilder().where("u.C_USERNAME = 'KASSA_RT01'");  // кассир, у которого всегда открыта касса` — зашитый пользователь стенда. Имя колонки логина взять из схемы в `CftSeed`/`CftDb`, логин — существующего кассира RTEST | Поиск кассира по подразделению и роли, как сейчас |
| 118 | а | — | — | Объединить методы: оставить один `tm_900118_ArrestOnCurrentAccount` с `@TestitStatus(autoTestId = "1100118", autoTestExternalId = "@900118")` и javadoc `Стенды: RTEST, INTEST (Oracle), PGRF1RT (PostgreSQL)`, тело — бывший `body()`. Метод TK900218 удалить. Это не дефект | — |
| 118 | б | 4 | — | Сетап: `.getObject()` вместо `.getRandomObject(10)` — параллельные прогоны берут один договор | `getRandomObject(10)` |
| 118 | в | 3 | ДС9 | Приватный `getAvailableBalance` в тесте с `NVL` и `SYSDATE`, как в старом `DepositDbSteps` | `COALESCE`, `CURRENT_DATE` |
| 118 | г | 5 | — | Приватные методы с запросами (`countHolds`, `getAvailableBalance`) без `@Step` — запросов не видно в Allure | `@Step` с номером договора |
| 118 | д | 1⛔ | ДС8 | Без изменений: `countHolds` считает все блокировки договора, `isPositive()` | Искать блокировку, созданную тестом: вид `ARREST`, сумма, состояние `ACTIVE`, дата — операционный день |
| 118 | е | 1⛔ | ДС8 | Вид «Арест», сумма 5 000,00 и состояние «Действует» не проверяются | Проверки вида, суммы и состояния найденной блокировки |
| 119 | а | 4 | ДС5 | Приватный `setZeroBalance` с `UPDATE Z#AC_FIN SET C_SALDO = 0`, вызов перед закрытием | Искать договор с нулевым остатком: `join("INNER JOIN Z#AC_FIN a ON a.ID = d.C_ACCOUNT").where("a.C_SALDO = 0")`. Если в сиде таких договоров нет — добавить их в `CftSeed` |
| 119 | б | 5 | — | Закрытие в `try { new CloseContractPageHelper(deposit).execute().clickOk(); } catch (Exception e) { log.error("Закрытие не прошло", e); }` — причина отказа ЦФТ теряется, тест падает на проверке состояния | Без `try` |
| 119 | в | 1⛔ | — | `.hasDateCloseEqualTo(deposit.getDateClose())` — договор сравнивается сам с собой | `hasDateCloseEqualTo(getOperDay())` |
| 119 | г | 1⛔ | — | Убрать `.whereR2AnnAccount(... ComStatusPrd.$CLOSE)` | Вернуть |
| 119 | д | SQL | ДС3 | В сетапе вместо `.withoutActiveCard()`: свой фрагмент `join("LEFT JOIN Z#R2_IP_CARDS ic ON ic.C_DEPOSIT = d.ID").where("ic.C_STATE <> 'ACTIVE'")` с комментарием `// без действующих карт` | `.withoutActiveCard()` |
| 120 | а | 1⛔ | — | `String error = …clickOk(true).getErrorText(); Assertions.assertThat(error).isNotEmpty();` — пройдёт при любой ошибке | `checkErrorTextEqualTo("Срок действия документа, удостоверяющего личность, истёк")` |
| 120 | б | 4 | — | В сетапе: `clPrivCriteria.getQueryBuilder().where("cp.ID = <ID клиента с истёкшим ДУЛ на RTEST>");  // клиент с истёкшим паспортом на RTEST` вместо `withDocDateEndExpired`. ID взять из `CftSeed`; на INTEST и PGRF1RT у этого клиента другой ID или его нет | `withDocDateEndExpired(getOperDay())` |
| 120 | в | 2 | — | Перед поиском договора: `TimeUnit.SECONDS.sleep(3);  // договор мог создаться асинхронно` | Удалить |
| 120 | г | 1⛔ | ДС6 | Без изменений: договор ищется только в состоянии «Работает» | Без фильтра по состоянию |
| 120 | д | 5 | — | `Assertions.assertThat(deposit == null).isTrue();` вместо `objectNotExist()` — при падении `expected true` без данных договора | `AssertionsUtil.assertThat(deposit).objectNotExist()` |

TK900118 получает 6 строк в таблице из-за объединения (метка «а» — не дефект). Дефектов в нём 5: б–е.

Ловушки части: ЛС1 (`CriteriaR2Deposit.withoutActiveHold`), ЛС2 (`getRandomObject(10)` в сетапе TK900116, TK900117, TK900119, TK900120 — у TK900118 там дефект Д118.б). Код снятых ЛС3, ЛС4, ЛС5 остаётся.

`TimeUnit.SECONDS.sleep` в части: 117, 120.

- [ ] **Step 3: Обновить кейс TK-900118 в `participant/sql/task.md`**

Заголовок `### TK-900118, TK-900218 «Наложение ареста на текущий счёт»` → `### TK-900118 «Наложение ареста на текущий счёт»`. Под предусловиями: `Кейс выполняется на стендах обеих СУБД: RTEST и INTEST (Oracle), PGRF1RT (PostgreSQL).` В тексте задания, где перечисляются кейсы и методы, убрать TK900218.

- [ ] **Step 4: Прогнать как есть на трёх стендах**

```bash
cd review-tasks/1a-autotest-review/participant/sql
for s in RTEST INTEST PGRF1RT; do echo "== $s"; mvn -q test -Dstand=$s 2>&1 | grep -E "Tests run:|FAIL|Exception" | head -15; done
```

Expected: компиляция без ошибок, 5 прогонов на стенд. Ожидаемо: RTEST — падают TK900116 (Д116.в), TK900117 (Д117.в), TK900119 (Д119.д); PGRF1RT — плюс TK900118 (Д118.в, `SYSDATE`); INTEST — TK900117 (Д117.г, чужие ID), TK900120 (Д120.б, клиента нет). Записать фактический итог для «Что видно в песочнице». Повторить RTEST трижды: результат не должен зависеть от `getRandomObject`.

- [ ] **Step 5: Исправленные версии и прогон**

Скопировать 5 тестов в `jury/fixed/sql/src/test/java/tests/PRODUCTS/R2_DEPOSIT/rko_fl/` и применить колонку «Исправление». Прогон:

```bash
SCR=/private/tmp/claude-501/-Users-paul-Documents-work-best-qa-contest/23501aa8-6b9f-4038-aaae-44488e6418c8/scratchpad
SRC=review-tasks/1a-autotest-review/participant/sql
rm -rf $SCR/sql-fixed && rsync -a --exclude target --exclude .m2 $SRC/ $SCR/sql-fixed/
cp -R review-tasks/1a-autotest-review/jury/fixed/sql/. $SCR/sql-fixed/
cd $SCR/sql-fixed && for s in RTEST INTEST PGRF1RT; do mvn -q test -Dstand=$s -Dmaven.repo.local=$OLDPWD/$SRC/.m2/repository 2>&1 | grep "Tests run:" | tail -1; done
```

Expected: на каждом стенде `Tests run: 5, Failures: 0, Errors: 0`.

- [ ] **Step 6: Черновик раздела ключа**

`jury/draft-sql.md` — по правилам шага 8 задачи 1. Ловушки ЛС1 и ЛС2 — старые формулировки, у ЛС2 места — четыре сетапа. В «Допустимых дополнительных замечаниях» оставить пункты про `formatted` вместо bind-переменных и про кавычки `Z#…` на PostgreSQL.

- [ ] **Step 7: Commit**

```bash
git add -A review-tasks/1a-autotest-review/participant/sql review-tasks/1a-autotest-review/jury/fixed/sql review-tasks/1a-autotest-review/jury/draft-sql.md
git commit -m "feat: 1а SQL — по 5 дефектов в каждом тесте, TK900218 внутри TK900118

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 3: 1а Playwright — 5 тестов

**Files:**
- Modify: `review-tasks/1a-autotest-review/participant/playwright/src/test/java/ru/rshb/pw/cards/CardPage.java`
- Modify: `…/cards/TK900111Test.java` … `TK900115Test.java`
- Modify: `…/playwright/task.md` (кейсы TK-900113, TK-900114, TK-900115)
- Create: `review-tasks/1a-autotest-review/jury/fixed/playwright/src/test/java/ru/rshb/pw/cards/TK9001{11..15}Test.java`
- Create: `review-tasks/1a-autotest-review/jury/draft-playwright.md`

**Interfaces:**
- Produces: в `CardPage` нет `isCardNumberMasked`; появляется `public Locator requisite(String testId)` → `page.getByTestId("requisites").getByTestId(testId)`.

- [ ] **Step 1: Исправить `CardPage.java`**

Удалить `isCardNumberMasked` и импорт `PlaywrightException`, добавить:

```java
public Locator requisite(String testId) {
    return page.getByTestId("requisites").getByTestId(testId);
}
```

`BaseTest.java` не трогать — там ловушка ЛП1.

- [ ] **Step 2: Внести дефекты**

| Тест | Метка | Пункт | Было | Что вносим | Исправление в `jury/fixed` |
| --- | --- | --- | --- | --- | --- |
| 111 | а | 5 | — | `@DisplayName("TK-900115 Блокировка карты с причиной «Компрометация»")` — номер скопирован, результат уйдёт в чужой кейс | `TK-900111` |
| 111 | б | 1⛔ | — | Шаг 1: убрать `assertThat(cardPage.status()).hasText("Активна")` | Вернуть |
| 111 | в | 2 | ДП1 | Без изменений: `page.waitForTimeout(5000)` | Удалить |
| 111 | г | PW | — | Статус после блокировки: `assertEquals("Заблокирована", cardPage.status().textContent());` — значение на момент вызова, без автоожидания; проходит только благодаря паузе | `assertThat(cardPage.status()).hasText("Заблокирована")` |
| 111 | д | 1⛔ | ДП2 | Без изменений: `if (reissueBanner.isVisible())` | `assertThat(reissueBanner).isVisible()` без `if` |
| 112 | а | 3 | ДП3 | Без изменений: долгоживущий JWT в коде | `api` из `BaseTest` |
| 112 | б | 1⛔ | ДП4 | Шаг 1: значение по умолчанию 200 000 не проверяется | `cardPage.openTab("Лимиты"); assertThat(cardPage.transferLimitInput()).hasValue("200 000")` |
| 112 | в | PW | — | Шаг 2, после сообщения: `assertEquals("150 000", page.querySelector("input[name='<имя поля из index.html песочницы>']").inputValue());` — `ElementHandle` без автоожидания и в обход локаторов | `assertThat(cardPage.transferLimitInput()).hasValue("150 000")` |
| 112 | г | PW | — | Шаг 3: `page.reload(); page.waitForLoadState(LoadState.NETWORKIDLE);` — документация Playwright не советует `networkidle` для тестов | Без `waitForLoadState` |
| 112 | д | 1⛔ | ДП4 | Шаг 3: после обновления значение не проверяется | `cardPage.openTab("Лимиты"); assertThat(cardPage.transferLimitInput()).hasValue("150 000")` |
| 113 | а | 3 | — | В `openSharedPage`: `setBaseURL("http://localhost:18080")` вместо `Config.baseUrl()` | `Config.baseUrl()` |
| 113 | б | 5 | — | В `openSharedPage` нет `context.tracing().start(...)`, а `closeContext` переопределён пустым — у упавших шагов нет трейса | Решается исправлением в: один тест с контекстом из `BaseTest` |
| 113 | в | 4 | ДП5 | Без изменений: три теста-шага с `@Order` и общей страницей | Один тест, шаги — `Allure.step` |
| 113 | г | 1⛔ | — | Шаг 2: кнопка «Снять временную блокировку» не проверяется (новый ожидаемый результат кейса) | `assertThat(page.getByRole(BUTTON, name "Снять временную блокировку")).isVisible()` |
| 113 | д | 2 | — | Шаг 3, перед действием: `Thread.sleep(1000);  // кнопка появляется с анимацией` | Удалить |
| 114 | а | 2 | — | После `openTab("Реквизиты")`: `page.waitForTimeout(2000);  // реквизиты подгружаются` | Удалить |
| 114 | б | 5 | ДП7 | Приватный `isCardNumberMasked()` в тесте (код из старого `CardPage`) с `catch (PlaywrightException e) { return false; }` и `assertTrue(isCardNumberMasked())` без сообщения | `assertThat(cardPage.requisite("cardNumber")).hasText(Pattern.compile("^•••• " + lastDigits(cardNumber) + "$"))` |
| 114 | в | 1⛔ | — | В `isCardNumberMasked` отдельной строкой `return text.startsWith("•••• ");` — последние 4 цифры не сверяются | Входит в исправление б |
| 114 | г | 1⛔ | ДП6 | Без изменений: `page.getByText(holderName).first()` | `assertThat(cardPage.requisite("holder")).hasText(cardInfo.holderName())` |
| 114 | д | PW | — | Срок действия (новый ожидаемый результат кейса): `assertThat(page.locator("xpath=(//dd)[3]")).hasText(cardInfo.expiry());` — позиционный xpath | `cardPage.requisite("<testId срока в index.html>")` |
| 115 | а | 1⛔ | — | Шаг 1: `assertThat(cardPage.balance()).containsText("0,00");` — пройдёт и для «10 000,00 ₽» | `hasText("0,00 ₽")` |
| 115 | б | PW | — | Шаг 2: клик по пункту меню с `new Locator.ClickOptions().setForce(true)` — без проверок доступности, сработает и на неактивном пункте | Обычный `click()` |
| 115 | в | 5 | — | Шаг 3: `assertTrue(response.ok());` вместо `assertEquals(200, …, "Код ответа сервиса закрытия карты")` | Вернуть `assertEquals` с сообщением |
| 115 | г | 2 | — | Новый шаг 4: `Thread.sleep(500);  // история обновляется не сразу` | Удалить |
| 115 | д | 1⛔ | — | Новый шаг 4: `cardPage.openTab("История"); assertThat(page.getByTestId("history")).isVisible();` — видна таблица, запись не проверяется | `assertThat(page.getByTestId("history").getByText("Закрытие карты")).isVisible()` |

Ловушки части: ЛП1 (`BaseTest`), ЛП3 (TK900115, `waitForResponse`), ЛП4 (TK900115, `assertThat(dialog).isHidden()`). Строки ЛП3 и ЛП4 не трогать, дефект Д115.в — на соседней строке.

Перед внесением Д112.в, Д114.д и Д115.д открыть `playwright/src/main/resources/efr/index.html` (или там, где лежит страница песочницы) и `EfrStubServer.java`: найти имя поля лимита переводов, `data-testid` срока действия, `data-testid` таблицы истории и текст записи о закрытии карты. Если записи о закрытии в истории нет — добавить её в заглушку (`EfrStore`), это правка песочницы, а не дефект.

- [ ] **Step 3: Обновить кейсы в `participant/playwright/task.md`**

TK-900113, шаг 2 — ожидаемый результат: `Статус карты — «Временно заблокирована»; отображается кнопка «Снять временную блокировку»`.

TK-900114, шаг 2: `Номер карты — «•••• » и последние 4 цифры; держатель и срок действия совпадают с данными выпуска карты`.

TK-900115 — новая строка:

```markdown
| 4 | Открыть вкладку «История» | Есть запись «Закрытие карты» |
```

- [ ] **Step 4: Прогнать как есть**

Run: `cd review-tasks/1a-autotest-review/participant/playwright && mvn -q test 2>&1 | grep -E "Tests run|FAIL|ERROR" | head -20`

Expected: компиляция без ошибок, 7 прогонов (у TK900113 три шага). Ожидаемо зелёные все; ДП5 по-прежнему виден при запуске шага отдельно (`mvn test -Dtest=TK900113Test#blockTemporarily`). Записать длительности (`target/surefire-reports`) для «Что видно в песочнице».

- [ ] **Step 5: Исправленные версии и прогон**

Скопировать 5 тестов в `jury/fixed/playwright/src/test/java/ru/rshb/pw/cards/`, применить «Исправление». TK900113 в исправленной версии — один `@Test`, без `@TestInstance`, `@TestMethodOrder`, `@BeforeAll` и переопределений, шаги через `io.qameta.allure.Allure.step("Шаг 1: …", () -> { … })`. Прогон по образцу шага 7 задачи 1 (папка `$SCR/playwright-fixed`, `mvn -q test -Dmaven.repo.local=…`).

Expected: `Tests run: 5, Failures: 0, Errors: 0`.

- [ ] **Step 6: Черновик раздела ключа и commit**

`jury/draft-playwright.md` по тем же правилам. Затем:

```bash
git add -A review-tasks/1a-autotest-review/participant/playwright review-tasks/1a-autotest-review/jury/fixed/playwright review-tasks/1a-autotest-review/jury/draft-playwright.md
git commit -m "feat: 1а Playwright — по 5 дефектов в каждом тесте

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 4: 1а — скрипт таблиц, ключ, Excel, `task.md`

**Files:**
- Create: `review-tasks/tools/build_sheets.py`, `review-tasks/tools/test_build_sheets.py`, `review-tasks/tools/requirements.txt`
- Modify: `.gitignore`
- Modify (переписать): `review-tasks/1a-autotest-review/jury/answer-key.md`
- Delete: `review-tasks/1a-autotest-review/jury/draft-*.md`
- Create: `review-tasks/1a-autotest-review/participant/answer-template.xlsx`, `review-tasks/1a-autotest-review/jury/scoring-sheet.xlsx`
- Modify: `review-tasks/1a-autotest-review/participant/{selenide,sql,playwright}/task.md`

**Interfaces:**
- Consumes: черновики `draft-selenide.md`, `draft-sql.md`, `draft-playwright.md` из задач 1–3.
- Produces: `python build_sheets.py <папка задания> [--show]`; формат строк ключа, который читает скрипт (ниже). Задача 8 использует тот же скрипт.

Формат строк ключа, которые читает скрипт:

```markdown
| Д101.1 | TK900101 | `TK900101Test.java:38` | Суть одной фразой | Засчитываем, если… |
| Л1 | `CardsHelper.java:103`, `CardsHelper.java:119` | Как выглядит замечание-попадание | Почему код корректен |
```

Ссылка на место — `Файл:строка` или `Файл:строка–строка` (короткое тире), несколько ссылок через запятую. Имя файла — как в песочнице, без пути.

- [ ] **Step 1: Окружение для скрипта**

```bash
cd review-tasks/tools
printf 'openpyxl==3.1.5\npytest==8.3.5\n' > requirements.txt
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
echo 'review-tasks/tools/.venv/' >> ../../.gitignore
```

- [ ] **Step 2: Написать тест скрипта**

`review-tasks/tools/test_build_sheets.py`:

```python
from pathlib import Path

import pytest
from openpyxl import load_workbook

import build_sheets


def make_task(tmp_path: Path, defects_per_test=5, tests=20, traps=10, clash=False) -> Path:
    (tmp_path / 'jury').mkdir()
    (tmp_path / 'participant').mkdir()
    lines = ['# Ключ', '', '| № | Тест | Файл:строки | Суть | Засчитываем, если… |', '| --- | --- | --- | --- | --- |']
    for t in range(tests):
        tk = f'TK9001{t + 1:02d}'
        for d in range(defects_per_test):
            lines.append(f'| Д1{t + 1:02d}.{d + 1} | {tk} | `{tk}Test.java:{10 + d}` | суть | признак |')
    lines += ['', '| № | Где | Попадание | Почему корректен |', '| --- | --- | --- | --- |']
    for n in range(traps):
        place = '`TK900101Test.java:10`' if clash and n == 0 else f'`Helper.java:{100 + n}`'
        lines.append(f'| Л{n + 1} | {place} | замечание | потому что |')
    (tmp_path / 'jury' / 'answer-key.md').write_text('\n'.join(lines), encoding='utf-8')
    return tmp_path


def test_builds_both_sheets(tmp_path):
    task = make_task(tmp_path)
    build_sheets.build(task)

    template = load_workbook(task / 'participant' / 'answer-template.xlsx').active
    assert template['A1'].value == 'Тест'
    assert [template.cell(row=r, column=1).value for r in range(2, 7)] == ['TK900101'] * 5
    assert template.cell(row=101, column=1).value == 'TK900120'

    sheet = load_workbook(task / 'jury' / 'scoring-sheet.xlsx').active
    assert sheet['A2'].value == 'Д101.1'
    assert sheet['A101'].value == 'Д120.5'
    assert sheet['A104'].value == 'Л1'
    assert sheet['A113'].value == 'Л10'
    assert sheet['F116'].value == '=MAX(0,SUM(F2:F101)-2*SUM(F104:F113))'


@pytest.mark.parametrize('kwargs, message', [
    ({'defects_per_test': 4}, 'TK900101: 4 дефекта'),
    ({'traps': 9}, 'ловушек 9'),
    ({'clash': True}, 'TK900101Test.java:10'),
])
def test_rejects_broken_key(tmp_path, kwargs, message):
    task = make_task(tmp_path, **kwargs)
    with pytest.raises(SystemExit, match=message):
        build_sheets.build(task)
```

- [ ] **Step 3: Запустить тест, убедиться, что падает**

Run: `cd review-tasks/tools && .venv/bin/pytest -q test_build_sheets.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_sheets'`.

- [ ] **Step 4: Написать скрипт**

`review-tasks/tools/build_sheets.py`:

```python
"""Шаблон ответа участника и лист подсчёта из ключа задания.

Запуск: python build_sheets.py ../1a-autotest-review [--show]
Читает jury/answer-key.md, пишет participant/answer-template.xlsx и jury/scoring-sheet.xlsx.
Падает, если в тесте не 5 дефектов, ловушек не 10 или дефект и ловушка указывают на одну строку.
--show печатает строки кода, на которые ссылается ключ, — для сверки глазами.
"""
import re
import sys
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

DEFECTS_PER_TEST = 5
TRAPS = 10
ROW = re.compile(r'^\|\s*(Д\d{3}\.\d|Л\d{1,2})\s*\|(.*)\|\s*$')
PLACE = re.compile(r'`([^`:]+):(\d+)(?:–(\d+))?`')
HEADER = Font(bold=True)
FILL = PatternFill('solid', fgColor='DDEBF7')
WRAP = Alignment(wrap_text=True, vertical='top')


def parse_key(key: Path):
    defects, traps = [], []
    for line in key.read_text(encoding='utf-8').splitlines():
        match = ROW.match(line)
        if match:
            cells = [c.strip() for c in match.group(2).split('|')]
            (defects if match.group(1).startswith('Д') else traps).append([match.group(1), *cells])
    return defects, traps


def places(text: str) -> set:
    found = set()
    for name, start, end in PLACE.findall(text):
        for line in range(int(start), int(end or start) + 1):
            found.add(f'{name}:{line}')
    return found


def check(defects, traps):
    errors = []
    per_test = Counter(row[1] for row in defects)
    for test, count in per_test.items():
        if count != DEFECTS_PER_TEST:
            errors.append(f'{test}: {count} дефекта, нужно {DEFECTS_PER_TEST}')
    if len(traps) != TRAPS:
        errors.append(f'ловушек {len(traps)}, нужно {TRAPS}')
    defect_places = set().union(*(places(row[2]) for row in defects)) if defects else set()
    for row in traps:
        for place in sorted(places(row[1]) & defect_places):
            errors.append(f'{row[0]} и дефект в одной строке: {place}')
    if errors:
        sys.exit('Ключ не прошёл проверку:\n' + '\n'.join(errors))


def header(sheet, titles, widths):
    for col, (title, width) in enumerate(zip(titles, widths), start=1):
        cell = sheet.cell(row=1, column=col, value=title)
        cell.font, cell.fill = HEADER, FILL
        sheet.column_dimensions[cell.column_letter].width = width
    sheet.freeze_panes = 'A2'


def build_template(defects, path: Path):
    book = Workbook()
    sheet = book.active
    sheet.title = 'Ответ'
    header(sheet, ['Тест', 'Файл:строка', 'Что не так', 'Почему это проблема', 'Как исправить'], [12, 28, 50, 50, 50])
    tests = list(dict.fromkeys(row[1] for row in defects))
    row = 2
    for test in tests:
        for _ in range(DEFECTS_PER_TEST):
            sheet.cell(row=row, column=1, value=test)
            for col in range(2, 6):
                sheet.cell(row=row, column=col).alignment = WRAP
            row += 1
    book.save(path)


def build_scoring(defects, traps, path: Path):
    book = Workbook()
    sheet = book.active
    sheet.title = 'Подсчёт'
    header(sheet, ['№', 'Тест / где', 'Место', 'Суть', 'Засчитываем, если…', '0 или 1'], [9, 14, 30, 45, 55, 9])
    zero_one = DataValidation(type='whole', operator='between', formula1='0', formula2='1', allow_blank=True)
    sheet.add_data_validation(zero_one)
    row = 2
    for number, test, place, essence, accept in defects:
        for col, value in enumerate([number, test, place.replace('`', ''), essence, accept], start=1):
            sheet.cell(row=row, column=col, value=value).alignment = WRAP
        zero_one.add(sheet.cell(row=row, column=6))
        row += 1
    last_defect = row - 1
    row += 1
    sheet.cell(row=row, column=1, value='Ловушки').font = HEADER
    row += 1
    first_trap = row
    for number, place, hit, why in traps:
        for col, value in enumerate([number, '', place.replace('`', ''), why, hit], start=1):
            sheet.cell(row=row, column=col, value=value).alignment = WRAP
        zero_one.add(sheet.cell(row=row, column=6))
        row += 1
    last_trap = row - 1
    row += 2
    sheet.cell(row=row, column=5, value='Итог: max(0, дефекты − 2 × ловушки)').font = HEADER
    sheet.cell(row=row, column=6, value=f'=MAX(0,SUM(F2:F{last_defect})-2*SUM(F{first_trap}:F{last_trap}))').font = HEADER
    book.save(path)


def show(defects, traps, task: Path):
    for row in defects + traps:
        cited = row[2] if row[0].startswith('Д') else row[1]
        for name, start, end in PLACE.findall(cited):
            skip = {'target', 'jury', '.m2', '.venv', 'build'}
            files = [p for p in task.rglob(name) if not skip & set(p.parts)]
            if not files:
                print(f'{row[0]}: файл {name} не найден')
                continue
            lines = files[0].read_text(encoding='utf-8').splitlines()
            for n in range(int(start), int(end or start) + 1):
                print(f'{row[0]} {name}:{n}: {lines[n - 1].strip() if n <= len(lines) else "<нет строки>"}')


def build(task: Path):
    defects, traps = parse_key(task / 'jury' / 'answer-key.md')
    check(defects, traps)
    build_template(defects, task / 'participant' / 'answer-template.xlsx')
    build_scoring(defects, traps, task / 'jury' / 'scoring-sheet.xlsx')


if __name__ == '__main__':
    target = Path(sys.argv[1]).resolve()
    if '--show' in sys.argv:
        show(*parse_key(target / 'jury' / 'answer-key.md'), target)
    else:
        build(target)
        print(f'Готово: {target.name}')
```

Ячейки листа подсчёта в тесте (`A104`, `F116`) соответствуют раскладке: 100 дефектов в строках 2–101, пустая 102, заголовок «Ловушки» в 103, ловушки 104–113, итог через одну строку — 116.

- [ ] **Step 5: Тест проходит**

Run: `cd review-tasks/tools && .venv/bin/pytest -q test_build_sheets.py`
Expected: `4 passed`.

- [ ] **Step 6: Собрать ключ 1а**

Переписать `review-tasks/1a-autotest-review/jury/answer-key.md` целиком. Структура:

1. Заголовок и «Только для жюри».
2. «Как считаем»: 20 тестов по 5 дефектов, +1 за дефект с местом, −2 за ловушку с общей суммы один раз, итог `max(0, дефекты − 2 × ловушки)`. Межтестовый дефект засчитывается у любого из двух тестов. Попадание в ловушку — участник считает место ошибкой и предлагает исправить; если сам объяснил, почему оно корректно, штрафа нет. Замечания вне ключа баллов не дают и не штрафуются, спорные — с Мариной Каприз. Лист подсчёта — `jury/scoring-sheet.xlsx`.
3. Пункты чек-листа 1–5 и технические категории — одной таблицей.
4. «Дефекты» — одна таблица на всё задание в формате выше, по порядку: Selenide TK900101–TK900110, SQL TK900116–TK900120, Playwright TK900111–TK900115. Строки — из черновиков.
5. «Ловушки» — одна таблица, Л1–Л10 по порядку места: `CardsHelper` (Л1, Л2), TK900106, TK900109, TK900110, `CriteriaR2Deposit`, сетапы SQL, `BaseTest`, TK900115 (две). Номера — по этому порядку.
6. «Верные замечания вне ключа» — короткий список из старых «допустимых» пунктов, которые остались верными.
7. «Что видно в песочнице» — три подраздела по частям, из черновиков.
8. «Что проверить перед запуском» — из старого ключа, без устаревших пунктов.

Таблицы «Самопроверка чек-листом» нет. Удалить `draft-selenide.md`, `draft-sql.md`, `draft-playwright.md`.

- [ ] **Step 7: Самопроверка ключа**

```bash
cd review-tasks/tools && .venv/bin/python build_sheets.py ../1a-autotest-review --show > /private/tmp/claude-501/-Users-paul-Documents-work-best-qa-contest/23501aa8-6b9f-4038-aaae-44488e6418c8/scratchpad/1a-show.txt; wc -l $_
```

Прочитать файл целиком: у каждого дефекта процитированная строка содержит заложенную ошибку, у каждой ловушки — корректный код, нет `<нет строки>` и «файл не найден». Затем для каждой пары дефектов одного теста с одним пунктом (например, Д104.3 и Д104.4, Д106.2–Д106.4, Д109.3 и Д109.4, Д118.4 и Д118.5) прочитать колонку «Засчитываем, если…»: в ней должно быть сказано, чем это замечание отличается от соседнего. Где не сказано — дописать.

- [ ] **Step 8: Построить Excel**

Run: `cd review-tasks/tools && .venv/bin/python build_sheets.py ../1a-autotest-review`
Expected: `Готово: 1a-autotest-review`, файлы `participant/answer-template.xlsx` и `jury/scoring-sheet.xlsx` созданы. Открыть лист подсчёта (`open review-tasks/1a-autotest-review/jury/scoring-sheet.xlsx`), поставить единицы в три дефекта и одну ловушку — итог должен стать 1.

- [ ] **Step 9: Обновить три `task.md` в 1а**

В каждом из `participant/selenide/task.md`, `participant/sql/task.md`, `participant/playwright/task.md`:

- Раздел «Формат ответа» заменить:

```markdown
## Формат ответа

Заполните таблицу `answer-template.xlsx` в папке `participant/`. В ней по 5 строк на каждый тест, строки можно добавлять.

| Тест | Файл:строка | Что не так | Почему это проблема | Как исправить |
| --- | --- | --- | --- | --- |
| TK900101 | `TK900101Test.java:12` | … | … | … |

Обязательно указывайте файл и строку. Замечание без места не засчитывается: «везде sleep» — не замечание.

Если проблема одного теста ломает другой тест, достаточно написать её у одного из них.

## Как считаются баллы

- Задание — это 20 тестов: 10 на Selenide, 5 на Java + SQL и 5 на Playwright. Все равноправны.
- В каждом тесте ровно 5 дефектов. За каждый найденный дефект с верной причиной — 1 балл, максимум 100.
- В тестах и общем коде есть ловушки — места, которые выглядят подозрительно, но написаны правильно. За каждое замечание, которое предлагает «исправить» правильный код, снимается 2 балла.
```

- Убрать слова «основная часть», «дополнительная часть», «по желанию», «обязательная» по всему файлу (`grep -n "основн\|дополнительн\|по желанию\|обязательн" task.md`).
- В Selenide `task.md` в разделе «Что нужно сделать» оставить упоминание `CardsHelper.java` как общего кода. В SQL `task.md` убрать упоминание `DepositDbSteps`.

- [ ] **Step 10: Прогон пользователя на ВДИ**

Сообщить пользователю, что 1а готова к прогону на ВДИ, и попросить запустить:

```text
cd participant\selenide && mvn test
cd participant\sql && mvn test & mvn test -Dstand=PGRF1RT & mvn test -Dstand=INTEST
cd participant\playwright && mvn test
```

и прислать хвост вывода. Расхождения с разделом «Что видно в песочнице» разобрать до задачи 5. В этом же сообщении перечислить отклонения от спецификации (раздел выше) и попросить подтвердить.

- [ ] **Step 11: Commit**

```bash
git add -A review-tasks/tools .gitignore review-tasks/1a-autotest-review
git commit -m "feat: 1а — ключ по тестам, шаблон ответа и лист подсчёта в Excel

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 5: 1д API — общий код и 10 тестов

**Files:**
- Modify: `review-tasks/1d-python-review/participant/python/tests/conftest.py`, `invest/steps/clients.py`, `invest/db/invest_db.py`
- Modify: `tests/api/**/test_9003{01..10}_*.py`
- Modify: `participant/python/task.md` (кейсы TK-900306, TK-900307, TK-900308, TK-900309)
- Create: `review-tasks/1d-python-review/jury/fixed/python/tests/api/**/test_9003{01..10}_*.py`
- Create: `review-tasks/1d-python-review/jury/draft-api.md`

**Interfaces:**
- Produces: фикстура `client_defaults` (session) — словарь полей нового клиента по умолчанию, `{'tariff': 'INVESTOR'}`; `create_client(invest_api, backoffice_token, tariff=None, extra=None, defaults=None)`; фикстура `client` удаляет только своего клиента; в `InvestDb` нет `get_last_order`, `count_executed_orders`, `count_today_orders`, `set_balance`, `delete_autotest_clients`; есть `get_tax_reports(client_id)`, `delete_client(client_id)`; `wait_tax_report_status` с `wait_fixed=500`.

- [ ] **Step 1: Исправить общий код**

`tests/conftest.py`:

```python
@pytest.fixture(scope='session')
def backoffice_token(invest_api):
    login, password = Config.user('backoffice')
    response = invest_api.backoffice_login(login, password)
    assert_that(response.status_code, is_(200), f'Не удалось войти в бэк-офис: {response.text}')
    return response.json()['token']


@pytest.fixture(scope='session')
def client_defaults():
    """Поля нового клиента по умолчанию."""
    return {'tariff': 'INVESTOR'}


@pytest.fixture
def client(invest_api, backoffice_token, invest_db, client_defaults, request):
    new_client = create_client(invest_api, backoffice_token, defaults=client_defaults)
    request.addfinalizer(lambda: invest_db.delete_client(new_client['id']))
    return new_client
```

Удалить `BACKOFFICE_LOGIN`, `BACKOFFICE_PASSWORD`, добавить `from framework.config import Config`.

`invest/steps/clients.py`:

```python
def create_client(invest_api, backoffice_token, tariff=None, extra=None, defaults=None):
    """Создаёт клиента через API бэк-офиса. По умолчанию — тариф «Инвестор»."""
    body = {**GenerateData().client(), **(defaults or {}), **(extra or {})}
    if tariff:
        body['tariff'] = tariff
    response = invest_api.create_client(body, backoffice_token)
    assert_that(response.status_code, is_(201), f'Клиент не создан: {response.text}')
    return {**response.json(), 'password': body['password']}
```

Перед этим проверить в `sandbox/service.py` (`create_client`), что сервис принимает поле `tariff` в теле и по умолчанию ставит `INVESTOR`.

`invest/db/invest_db.py`: `get_client_by_login` — параметр `?`; в `wait_order_status` — `assert order['status'] == status, f"Поручение {order_id}: статус {order['status']}, ожидался {status}"`; удалить `get_last_order`, `count_executed_orders`, `count_today_orders`, `set_balance`, `delete_autotest_clients`; `get_today_tax_reports` заменить на `get_tax_reports(client_id)` (`SELECT * FROM tax_report WHERE client_id = ? ORDER BY id DESC`); добавить `delete_client(client_id)` (`DELETE FROM client WHERE id = ?`; если у клиента есть зависимые строки и сервис удаляет каскадом только клиента — посмотреть, как удалял старый `delete_autotest_clients`, и сделать так же); `wait_tax_report_status` — `@retry(wait_fixed=500, stop_max_delay=15000)`. Строки ловушек Л2 (`currency = 'RUB'`) и Л3 (`@retry(wait_fixed=500, …)` у `wait_order_status`) не трогать.

После правки: `grep -rn "get_last_order\|count_executed\|count_today\|set_balance\|delete_autotest\|get_today_tax" tests/` — список мест, которые надо переписать в шаге 2.

- [ ] **Step 2: Внести дефекты**

| Тест | Метка | Пункт | Было | Что вносим | Исправление в `jury/fixed` |
| --- | --- | --- | --- | --- | --- |
| 301 | а | 5 | — | `@reporting.id(900310)` — номер скопирован | `900301` |
| 301 | б | 1⛔ | — | `re.fullmatch(r'БД-\d+', …)` — кейс требует 7 цифр | `r'БД-\d{7}'` |
| 301 | в | 1⛔ | — | `assert_that(agreements[0]['status'], 'Статус договора в БД')` — проверка одного аргумента на истинность | `equal_to('ACTIVE')` |
| 301 | г | 1⛔ | — | `assert (account['balance'] == 0, 'Остаток на новом счёте')` — кортеж всегда истинен (pytest пишет `PytestAssertRewriteWarning`) | `assert_that(account['balance'], equal_to(0), …)` |
| 301 | д | 4 | Д2 | Новый шаг в конце: `with reporting.step('Убрать за собой'): invest_db.execute("DELETE FROM client WHERE login LIKE 'autotest%'")` | Удалить: фикстура удаляет своего клиента |
| 302 | а | pytest | — | Метод `second_iis_rejected` без префикса `test_` — pytest его не собирает, тест не запускается | `test_second_iis_rejected` |
| 302 | б | 5 | — | После второй попытки: `print(response.status_code, response.text)` вместо проверки | Удалить |
| 302 | в | 1⛔ | Д11 | Без изменений: `is_not(201)` | `equal_to(409)` |
| 302 | г | 1⛔ | Д12 | Текст ошибки «У клиента уже есть действующий ИИС» не проверяется | `assert_that(response.json()['errorMessage'], equal_to(…))` |
| 302 | д | 1⛔ | Д12 | Число ИИС в БД не проверяется | `has_length(1)` по договорам типа `IIS` из `invest_db.get_agreements` |
| 303 | а | 4 | Д7 | Локальный запрос `invest_db.query("SELECT COUNT(*) AS cnt FROM money_order WHERE status = 'EXECUTED'", fetch_one=True)['cnt']` до и после | `invest_db.wait_order_status(order['id'], 'EXECUTED')` |
| 303 | б | 1⛔ | — | `assert_that(response.json()['status'], is_in(['NEW', 'EXECUTED']), …)` — не отличает новое поручение | `equal_to('NEW')` |
| 303 | в | 2 | Д13 | Без изменений: `time.sleep(3)` | Ожидание статуса (см. а) |
| 303 | г | 1⛔ | — | `assert_that(balance, contains_string('10000'), 'Остаток по API')` — пройдёт для «110000.00» | `equal_to('10000.00')` |
| 303 | д | SQL | — | Остаток в БД: `invest_db.query('SELECT balance FROM account WHERE agreement_id = ?', agreement['id'], fetch_one=True)` — без валюты, у договора могут быть счета в разных валютах | `invest_db.get_account(...)` |
| 304 | а | 4 | Д10 | `invest_db.execute('UPDATE account SET balance = ? WHERE agreement_id = ?', 5000, agreement['id'])` | Пополнить через API и дождаться исполнения |
| 304 | б | 2 | — | После `UPDATE`: `time.sleep(1)  # дать сервису подхватить остаток` | Удалить |
| 304 | в | 5 | — | Проверка текста ошибки в `try: … except AssertionError: pytest.skip('Текст ошибки на стенде меняется')` — падение превращается в пропуск | Без `try` |
| 304 | г | 1⛔ | Д8 | Локальный запрос `… AND created_at = date('now')` | `type = 'WITHDRAW'` по договору без даты, `equal_to(0)` |
| 304 | д | 1⛔ | — | `assert_that(account['balance'], greater_than_or_equal_to(5000), 'Остаток на счёте')` | `equal_to(5000)` |
| 305 | а | 3 | Д1 | `invest_api.backoffice_login('bo_operator1', 'Oper1#Playground')` в тесте вместо фикстуры `backoffice_token` | Фикстура `backoffice_token` |
| 305 | б | 4 | Д3 | `client_defaults['tariff'] = 'TRADER'` и `create_client(…, defaults=client_defaults)` — общий словарь меняется и не возвращается, все клиенты дальше на «Трейдере» (TK900309, TK900311, TK900320) | `create_client(…, tariff='TRADER')` |
| 305 | в | 5 | — | `refill = invest_api.refill(…).json()` без проверки кода — при отказе `KeyError: 'id'` | Проверка 201 с текстом ответа |
| 305 | г | 4 | Д6 | Локальный запрос «последнего» вывода: `SELECT * FROM money_order WHERE type = 'WITHDRAW' ORDER BY created_at DESC LIMIT 1` | `response.json()['id']` |
| 305 | д | 1⛔ | — | Убрать проверку остатка 7 000 | Вернуть |
| 306 | а | 3 | — | `invest_db = InvestDb('build/invest.db')` в тесте вместо фикстуры — путь к файлу песочницы | Фикстура `invest_db` |
| 306 | б | 4 | Д14 | Без изменений: `tax_period = 2025` | `date.today().year - 1` |
| 306 | в | 1⛔ | Д15 | Статус `ORDERED` в ответе не проверяется | `equal_to('ORDERED')` по ответу |
| 306 | г | SQL | Д9 | Локальный запрос `… AND date(registered_at) = date('now')` | `date('now', 'localtime')` |
| 306 | д | 1⛔ | Д15 | Статус `ORDERED` в БД не проверяется | `equal_to('ORDERED')` по строке БД |
| 307 | а | 1⛔ | — | `@pytest.mark.parametrize('tax_period', [CURRENT_YEAR, CURRENT_YEAR], ids=['current_year', 'next_year'])` — следующий год не проверяется | `CURRENT_YEAR + 1` |
| 307 | б | pytest | — | `pytest.raises(Exception)` — пройдёт и при ошибке соединения | `pytest.raises(HTTPError)` |
| 307 | в | 1⛔ | Д16 | Без изменений: проверки внутри `with pytest.raises` | Вынести после блока |
| 307 | г | SQL | — | «Заявка не создана»: `invest_db.query("SELECT COUNT(*) AS cnt FROM tax_report WHERE client_id = ? AND status = 'Ordered'", …)` — статусы пишутся заглавными, счётчик всегда 0 | `invest_db.get_tax_reports(client['id'])`, `has_length(0)` |
| 307 | д | 1⛔ | — | Новый ожидаемый результат кейса: в списке справок клиента по API нет новой заявки. Тест делает `invest_api.get_tax_reports(token)` и не проверяет | `has_length(0)` по ответу. Если в `InvestApi` нет `get_tax_reports` — добавить (`GET /api/v1/tax-reports`, маршрут в песочнице есть) |
| 308 | а | 3 | Д17 | Без изменений: `requests.post("http://localhost:18300/…")` | `invest_api.close_agreement(...)` |
| 308 | б | 5 | — | Текст ошибки проверяется раньше кода: при успешном закрытии `KeyError: 'errorMessage'` | Сначала код |
| 308 | в | 1⛔ | — | `contains_string('выведите')` | `equal_to('Для закрытия договора выведите денежные средства')` |
| 308 | г | 1⛔ | — | Новый ожидаемый результат кейса: по API статус договора `ACTIVE`. Тест делает `invest_api.get_agreement(...)` и результат не проверяет | `equal_to('ACTIVE')` |
| 308 | д | 1⛔ | — | Новый ожидаемый результат кейса: остаток 1 000 не изменился. Не проверяется | `invest_db.get_account(...)`, `equal_to(1000)` |
| 309 | а | 1⛔ | — | Новый шаг кейса: перед сменой тариф клиента «Инвестор». Не проверяется | `equal_to('INVESTOR')` по `GET /profile` |
| 309 | б | 1⛔ | — | `assert_that(response.json()['tariff'], 'Тариф в ответе')` — один аргумент | `equal_to('TRADER')` |
| 309 | в | SQL | — | История: `invest_db.query('SELECT * FROM tariff_history WHERE client_id = ? LIMIT 1', …)` — без `ORDER BY` | `ORDER BY id DESC` |
| 309 | г | 5 | Д18 | `assert_that(row['old_tariff'] == 'INVESTOR' and row['new_tariff'] == 'TRADER', is_(True))` без сообщения | `has_entries(old_tariff='INVESTOR', new_tariff='TRADER')` с описанием |
| 309 | д | 1⛔ | — | Новый ожидаемый результат кейса: в профиле по API тариф `TRADER`. Запрос есть, проверки нет | `equal_to('TRADER')` |
| 310 | а | 3 | Д20 | Без изменений: логин и пароль клиента стенда константами | Свой клиент через фикстуру `client` |
| 310 | б | 4 | Д20 | Без изменений: тест блокирует общего клиента и не разблокирует | Свой клиент (см. а) |
| 310 | в | 1⛔ | Д19 | Без изменений: `xfail` без `strict` | Убрать `xfail` |
| 310 | г | 2 | — | После трёх попыток: `time.sleep(1)  # блокировка применяется не сразу` | Удалить |
| 310 | д | SQL | Д4 | Статус в БД: `invest_db.query(f"SELECT status FROM client WHERE login = '{LOGIN}'", fetch_one=True)` | `invest_db.get_client_by_login(...)` |

Ловушки части: Л2, Л3 (`invest_db.py`), Л5 (TK900301, `assert response.status_code == 201`), Л7 (TK900304, `'5000.01'`), Л9 (TK900308, цикл опроса), Л10 (TK900310, цикл трёх попыток). Строки ловушек не трогать.

`time.sleep` в части: 303, 304, 310.

- [ ] **Step 3: Обновить кейсы в `task.md`**

- TK-900307, шаг 2: `Заявка на справку не создана ни в БД, ни в списке справок клиента по API`.
- TK-900308: шаг 2 — `Статус договора в БД и по API — ACTIVE; остаток — 1 000`.
- TK-900309: новый шаг 1 `Открыть профиль клиента | Тариф — «Инвестор»`, остальные сдвинуть; в шаге проверки — `в профиле по API тариф TRADER`.

- [ ] **Step 4: Прогнать как есть**

```bash
cd review-tasks/1d-python-review/participant/python && source .venv/bin/activate
pytest tests/api -q 2>&1 | tail -15
pytest tests/api -q -n 4 2>&1 | tail -5
```

Expected: нет ошибок сборки (кроме ожидаемого «не собран» TK900302 — `pytest --collect-only -q tests/api | grep 900302` пусто). Ожидаемо видны: Д303.а (падает всегда), Д305.б (TK900309 падает в полном прогоне), Д310.в (`XPASS`), Д301.г (`PytestAssertRewriteWarning` в сводке), Д301.д (с `-n 4` падают соседние тесты). Записать фактический итог.

- [ ] **Step 5: Исправленные версии и прогон**

Скопировать 10 тестов в `jury/fixed/python/tests/api/…` с той же структурой папок, применить «Исправление».

```bash
SCR=/private/tmp/claude-501/-Users-paul-Documents-work-best-qa-contest/23501aa8-6b9f-4038-aaae-44488e6418c8/scratchpad
SRC=review-tasks/1d-python-review/participant/python
rm -rf $SCR/python-fixed && rsync -a --exclude .venv --exclude build $SRC/ $SCR/python-fixed/
cp -R review-tasks/1d-python-review/jury/fixed/python/. $SCR/python-fixed/
cd $SCR/python-fixed && $OLDPWD/$SRC/.venv/bin/pytest tests/api -q 2>&1 | tail -3 && $OLDPWD/$SRC/.venv/bin/pytest tests/api -q -n 4 2>&1 | tail -3
```

Expected: `11 passed` (у TK900307 два набора) в обоих прогонах.

- [ ] **Step 6: Черновик раздела ключа и commit**

`jury/draft-api.md` по правилам шага 8 задачи 1. Д305.2 — места в TK900305 и симптом в TK900309, TK900311, TK900320.

```bash
git add -A review-tasks/1d-python-review/participant/python review-tasks/1d-python-review/jury/fixed review-tasks/1d-python-review/jury/draft-api.md
git commit -m "feat: 1д API — по 5 дефектов в каждом тесте, общий код без дефектов

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 6: 1д Kafka — 5 тестов

**Files:**
- Modify: `review-tasks/1d-python-review/participant/python/invest/kafka/kafka_steps.py`
- Modify: `tests/kafka/test_9003{11..15}_*.py`
- Modify: `participant/python/task.md` (кейсы TK-900311, TK-900313, TK-900315)
- Create: `review-tasks/1d-python-review/jury/fixed/python/tests/kafka/test_9003{11..15}_*.py`
- Create: `review-tasks/1d-python-review/jury/draft-kafka.md`

**Interfaces:**
- Produces: `KafkaSteps.read_messages` пробрасывает ошибку QA Service; отладочный вывод через `logging`; новый `KafkaSteps.wait_record(topic, condition, timeout=15)` → `dict` с полями `key` и `value` (как `wait_message`, но возвращает сообщение целиком).

- [ ] **Step 1: Исправить `kafka_steps.py`**

```python
log = logging.getLogger('kafka')

def read_messages(self, topic, seconds_ago=60):
    return self.qa_kafka.subscribe(topic, self.cluster_id, seconds_ago=seconds_ago)['messages']

def wait_record(self, topic, condition, timeout=15):
    """Ждёт сообщение, для которого condition(value) истинно, и возвращает его целиком: key и value."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for message in reversed(self.read_messages(topic)):
            if condition(message['value']):
                return message
        log.info('В топике %s пока нет нужного сообщения', topic)
        time.sleep(0.5)
    raise AssertionError(f'Сообщение в топике {topic} не пришло за {timeout} с')

def wait_message(self, topic, condition, timeout=15):
    """Ждёт сообщение, для которого condition(value) истинно, и возвращает его value."""
    return self.wait_record(topic, condition, timeout)['value']
```

Убрать импорт `HTTPError`, добавить `logging`. Перед этим проверить в `sandbox/kafka.py`, что сообщение от `subscribe` содержит `key`. Цикл ожидания — ловушка ЛК1, теперь она в `wait_record`. `send_payment` не трогать.

- [ ] **Step 2: Внести дефекты**

| Тест | Метка | Пункт | Было | Что вносим | Исправление в `jury/fixed` |
| --- | --- | --- | --- | --- | --- |
| 311 | а | 2 | — | `time.sleep(1)  # событие публикуется не сразу` перед поиском | Удалить: `wait_record` ждёт сам |
| 311 | б | 3 | — | Топик строкой `'invest.client-events'` вместо `Topics.CLIENT_EVENTS` | `Topics.CLIENT_EVENTS` |
| 311 | в | 4 | — | Условие `lambda value: value.get('eventType') == 'CLIENT_CREATED'` — первое попавшееся событие о любом клиенте | По `login` своего клиента |
| 311 | г | 1⛔ | — | Из `has_entries` убрать `'tariff': 'INVESTOR'` с комментарием `# тариф в событии приходит не всегда` | Вернуть |
| 311 | д | Kafka | — | Новый ожидаемый результат кейса: ключ сообщения — id клиента. Тест получает сообщение через `wait_record`, ключ не проверяет | `assert_that(record['key'], equal_to(str(client['id'])), 'Ключ сообщения')` — формат ключа взять из песочницы |
| 312 | а | Kafka | — | Поступление отправляется вручную `qa_kafka.send(Topics.INCOMING_PAYMENTS, kafka.cluster_id, payment)` без ключа — сообщения одного договора могут попасть в разные партиции. Тело — как в `send_payment` | `kafka.send_payment(...)` |
| 312 | б | 2 | ДК4 | Без изменений: `time.sleep(2)` | Удалить |
| 312 | в | 5 | ДК2 | `print(f'[KAFKA] события: {messages}')` перед выбором события | Удалить |
| 312 | г | 4 | ДК5 | Без изменений: последнее сообщение топика | `kafka.wait_message(Topics.MONEY_ORDERS, lambda v: v['agreementNumber'] == agreement['number'] and v['source'] == 'CFT')` |
| 312 | д | 1⛔ | — | `assert_that(account['balance'], greater_than(0), 'Остаток на счёте')` | `equal_to(1000)` |
| 313 | а | 4 | ДК6 | Без изменений: `PAYMENT_ID` зашит | `str(uuid.uuid4())` на каждый прогон, повтор — с тем же значением |
| 313 | б | 1⛔ | — | Новый ожидаемый результат шага 1: остаток 1 000 после первого зачисления. Не проверяется | `equal_to(1000)` после ожидания события |
| 313 | в | 1⛔ | ДК7 | Без изменений: проверки сразу после повтора | Контрольное поступление с новым `PaymentId` и ожидание его события |
| 313 | г | 1⛔ | — | Новый ожидаемый результат шага 3: в топике одно событие `EXECUTED` по договору на сумму 1 000. Не проверяется | Отфильтровать `kafka.read_messages(Topics.MONEY_ORDERS)` по договору и сумме, `has_length(1)` |
| 313 | д | 5 | — | `assert_that(len(invest_db.get_orders(agreement['id'])) == 1, is_(True))` | `has_length(1)` с описанием |
| 314 | а | 3 | — | Топик строкой `'sofr.get-tax-report-info-request'` | `Topics.TAX_REPORT_REQUEST` |
| 314 | б | 5 | — | Ожидание в `try: … except HTTPError: pytest.skip('Топик СОФР недоступен на стенде')` — ошибка настройки превращается в пропуск | Без `try` |
| 314 | в | 4 | ДК8 | Без изменений: поиск только по году | По `ClientId` |
| 314 | г | 1⛔ | ДК9 | `ClientId` не проверяется | `equal_to(client['id'])` |
| 314 | д | 1⛔ | ДК9 | `AgreementNumbers` не проверяется | `equal_to([agreement['number']])` — формат взять из песочницы |
| 315 | а | 1⛔ | — | Новый ожидаемый результат шага 1: заявка в статусе `ORDERED`. Не проверяется | `equal_to('ORDERED')` по ответу |
| 315 | б | 3 | ДК10 | Без изменений: кластер `'invest-kafka'` | `kafka.cluster_id` |
| 315 | в | 2 | ДК3 | Локальная функция в модуле теста `@retry(stop_max_delay=15000) def wait_report(invest_db, report_id, status)` — без паузы между попытками | `@retry(wait_fixed=500, stop_max_delay=15000)` или `invest_db.wait_tax_report_status` |
| 315 | г | SQL | — | В этой функции запрос `SELECT * FROM tax_report WHERE client_id = ?` с `fetch_one` — справка по клиенту, а не по `id` заявки | `WHERE id = ?` |
| 315 | д | 1⛔ | — | Новый ожидаемый результат шага 4: по API имя файла из ответа СОФР. Проверяется только статус | `equal_to(file_name)` по полю файла в ответе API — имя поля взять из песочницы |

Ловушки части: ЛК1 (`kafka_steps.py`, цикл в `wait_record`), ЛК5 (TK900314, `RequestTime` и `date.today()`). Код ЛК2, ЛК4, ЛК6 остаётся.

`time.sleep` в части: 311, 312.

- [ ] **Step 3: Обновить кейсы в `task.md`**

- TK-900311, шаг 2: дописать `; ключ сообщения — id клиента`.
- TK-900313, шаг 1: `В топике invest.money-orders есть событие EXECUTED по этому договору; остаток — 1 000`. Шаг 3: дописать `; в топике invest.money-orders одно событие EXECUTED по договору`.
- TK-900315: шаг 1 — `Ответ 201; статус заявки — ORDERED`; шаг 4 — `…по API статус READY и имя файла из ответа`.

- [ ] **Step 4: Прогнать как есть и с исправлениями**

```bash
cd review-tasks/1d-python-review/participant/python && source .venv/bin/activate
pytest tests/kafka -q 2>&1 | tail -10
pytest -q 2>&1 | tail -10
```

Expected: в `pytest tests/kafka` падает TK900312 (Д312.г). TK900311 в полном прогоне, скорее всего, остаётся зелёным, хотя клиент уже на «Трейдере» (Д305.2): тариф в событии не проверяется (Д311.г). Это хорошо для ключа — пример того, как один дефект прячет другой. Записать фактический результат. Затем исправленные версии — по образцу шага 5 задачи 5, `pytest tests/kafka -q` и `pytest -q -n 4` в копии. Expected: все зелёные.

- [ ] **Step 5: Черновик раздела ключа и commit**

`jury/draft-kafka.md`, затем:

```bash
git add -A review-tasks/1d-python-review/participant/python review-tasks/1d-python-review/jury/fixed review-tasks/1d-python-review/jury/draft-kafka.md
git commit -m "feat: 1д Kafka — по 5 дефектов в каждом тесте

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 7: 1д Playwright — 5 тестов

**Files:**
- Modify: `review-tasks/1d-python-review/participant/python/tests/ui/conftest.py`, `invest/pages/cabinet.py`
- Modify: `tests/ui/test_9003{16..20}_*.py`
- Modify: `participant/python/task.md` (кейсы TK-900316, TK-900318, TK-900320)
- Create: `review-tasks/1d-python-review/jury/fixed/python/tests/ui/test_9003{16..20}_*.py`
- Create: `review-tasks/1d-python-review/jury/draft-ui.md`

**Interfaces:**
- Produces: `cabinet_client` — фикстура уровня функции; в `AgreementPage` нет `balance()`, есть `balance_locator()`.

- [ ] **Step 1: Исправить общий код**

`tests/ui/conftest.py`: у `cabinet_client` убрать `scope='session'`, фикстура принимает `client_defaults` и передаёт `defaults=client_defaults` в `create_client`. `invest/pages/cabinet.py`: удалить метод `balance()`. Ловушки ЛП1 (`base_url`) и ЛП2 (`row` с фильтром по номеру) не трогать.

- [ ] **Step 2: Внести дефекты**

| Тест | Метка | Пункт | Было | Что вносим | Исправление в `jury/fixed` |
| --- | --- | --- | --- | --- | --- |
| 316 | а | 3 | ДП3 | Без изменений: `page.goto('http://localhost:18300/cabinet/')` | `page.goto('/cabinet/')` |
| 316 | б | PW | — | После входа: `page.wait_for_load_state('networkidle')` | Удалить |
| 316 | в | 1⛔ | — | `expect(page.get_by_test_id('client-name')).to_contain_text(client['lastName'])` — только фамилия | `to_have_text(full_name)` |
| 316 | г | PW | — | Строка договора: `page.get_by_test_id('agreement-row').first` вместо `AgreementsPage(page).row(number)` — первая строка списка | `AgreementsPage(page).row(agreement['number'])` |
| 316 | д | 1⛔ | — | Новый ожидаемый результат кейса: статус договора «Действует». Не проверяется | `expect(row).to_contain_text('Действует')` или локатор статуса из страницы кабинета |
| 317 | а | 1⛔ | — | Уведомление: `to_contain_text('создано')` | `to_have_text('Поручение на пополнение создано')` |
| 317 | б | 1⛔ | — | Статус «Новое» сразу после создания не проверяется | `expect(first.get_by_test_id('order-status')).to_have_text('Новое')` |
| 317 | в | PW | — | `cabinet.get_by_role('button', name='Создать поручение').click(force=True)` вместо `agreement_page.refill(10000)` (поле суммы заполняется тут же) | `agreement_page.refill(10000)` |
| 317 | г | 2 | ДП4 | Без изменений: `wait_for_timeout(5000)` | Удалить |
| 317 | д | PW | ДП2 | `assert agreement_page.balance_locator().inner_text() == '10 000,00 ₽'` | `expect(agreement_page.balance_locator()).to_have_text('10 000,00 ₽')` |
| 318 | а | 2 | — | После вывода: `time.sleep(1)  # история обновляется раз в секунду` | Удалить |
| 318 | б | 5 | — | `try: expect(alert).to_have_text('Недостаточно средств для вывода') except AssertionError: pass  # текст на стенде иногда другой` | Без `try` |
| 318 | в | 1⛔ | — | Отдельной проверкой: `expect(alert).to_contain_text('Недостаточно')` | Входит в исправление б |
| 318 | г | 1⛔ | ДП5 | Без изменений: `to_have_count(0)` сразу | Перезагрузить страницу, дождаться истории, проверить через API |
| 318 | д | 1⛔ | — | Новый ожидаемый результат кейса: остаток 5 000,00 ₽ после отказа. Не проверяется | `expect(agreement_page.balance_locator()).to_have_text('5 000,00 ₽')` |
| 319 | а | 3 | — | В модуле теста фикстура `browser_context_args`, которая подставляет `'base_url': 'http://localhost:18300'` | Удалить фикстуру |
| 319 | б | 4 | — | `year = 2025` | `date.today().year - 1` |
| 319 | в | PW | — | `assert cabinet.get_by_role('alert').inner_text() == f'Справка за {year} год заказана'` | `expect(...).to_have_text(...)` |
| 319 | г | 2 | — | `cabinet.wait_for_timeout(1000)` перед проверкой списка | Удалить |
| 319 | д | 1⛔ | ДП6 | Без изменений: скриншот вместо проверки строки | `expect(reports_page.report_rows().filter(has_text=str(year))).to_contain_text('Заказана')` |
| 320 | а | 5 | — | Вместо `expect(profile.tariff()).to_have_text('Инвестор')`: `if profile.tariff().inner_text() != 'Инвестор': pytest.skip('Клиент уже на «Трейдере»')` — симптом Д305.2 прячется в пропуск | Вернуть `expect` |
| 320 | б | 1⛔ | — | Новый ожидаемый результат кейса: текст окна подтверждения «Перейти на тариф «Трейдер»?». Обработчик принимает окно, текст не проверяет | Сохранить `dialog.message` в обработчике и сравнить |
| 320 | в | 2 | — | `cabinet.wait_for_timeout(2000)` после клика | Удалить |
| 320 | г | 1⛔ | ДП7 | Без изменений: `to_contain_text('Трейдер')` | `to_have_text('Тариф изменён на «Трейдер»')` |
| 320 | д | 1⛔ | ДП7 | Тариф в профиле после смены не проверяется | `expect(profile.tariff()).to_have_text('Трейдер')` |

Перед Д316.д и Д320.б посмотреть разметку кабинета (`sandbox/` — статические файлы кабинета) и текст окна подтверждения. Если статуса договора в списке нет — заменить Д316.д на непроверенный тип счёта или другой видимый на странице атрибут договора и поправить кейс соответственно.

Ловушки части: ЛП3 (TK900317, `timeout=15_000`), ЛП5 (TK900320, `cabinet.once('dialog', …)` — строку обработчика оставить с `once`, проверку текста добавить внутрь лямбды так, чтобы строка `once` не менялась; если это невозможно, ЛП5 переносится на новую строку с `once`). Код ЛП1, ЛП2, ЛП4 остаётся.

`wait_for_timeout` в части: 317, 319, 320. `time.sleep`: 318.

- [ ] **Step 3: Обновить кейсы в `task.md`**

- TK-900316, шаг 2: `Тип — «Брокерский договор»; статус — «Действует»; остаток — «0,00 ₽»`.
- TK-900318, шаг 2: дописать `; остаток — «5 000,00 ₽»`.
- TK-900320, шаг 2: `Открыто окно подтверждения «Перейти на тариф «Трейдер»?»; после подтверждения — уведомление «Тариф изменён на «Трейдер»»; в профиле тариф — «Трейдер»`.

- [ ] **Step 4: Прогнать как есть и с исправлениями**

```bash
cd review-tasks/1d-python-review/participant/python && source .venv/bin/activate
pytest tests/ui -q --durations=0 2>&1 | tail -20
pytest -q 2>&1 | tail -10
```

Записать фактический итог: UI-часть и полный прогон проекта. Затем исправленные версии в копии: `pytest -q` и `pytest -q -n 4` — весь проект зелёный.

- [ ] **Step 5: Черновик раздела ключа и commit**

`jury/draft-ui.md`, затем:

```bash
git add -A review-tasks/1d-python-review/participant/python review-tasks/1d-python-review/jury/fixed review-tasks/1d-python-review/jury/draft-ui.md
git commit -m "feat: 1д Playwright — по 5 дефектов в каждом тесте

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 8: 1д — ключ, Excel, `task.md`

**Files:**
- Modify (переписать): `review-tasks/1d-python-review/jury/answer-key.md`
- Delete: `review-tasks/1d-python-review/jury/draft-*.md`
- Create: `review-tasks/1d-python-review/participant/answer-template.xlsx`, `review-tasks/1d-python-review/jury/scoring-sheet.xlsx`
- Modify: `review-tasks/1d-python-review/participant/python/task.md`

**Interfaces:**
- Consumes: `review-tasks/tools/build_sheets.py` из задачи 4; черновики задач 5–7.

- [ ] **Step 1: Собрать ключ 1д**

Структура — как в шаге 6 задачи 4. Порядок дефектов: API TK900301–TK900310, Kafka TK900311–TK900315, Playwright TK900316–TK900320. Ловушки Л1–Л10 по порядку места: `invest_db.py` (две подряд), TK900301, TK900304, TK900308, TK900310, `kafka_steps.py`, TK900314, TK900317, TK900320. Абзац про стиль кода команды СИ — оставить. Удалить черновики.

- [ ] **Step 2: Самопроверка ключа и Excel**

```bash
cd review-tasks/tools
.venv/bin/python build_sheets.py ../1d-python-review --show > /private/tmp/claude-501/-Users-paul-Documents-work-best-qa-contest/23501aa8-6b9f-4038-aaae-44488e6418c8/scratchpad/1d-show.txt
.venv/bin/python build_sheets.py ../1d-python-review
```

Сверка — как в шаге 7 задачи 4. Пары, которые надо развести в «Засчитываем, если…»: Д302.3–Д302.5, Д306.3 и Д306.5, Д310.1 и Д310.2, Д314.4 и Д314.5, Д318.2 и Д318.3, Д320.4 и Д320.5. Expected: `Готово: 1d-python-review`; лист подсчёта даёт 1 при трёх найденных дефектах и одной ловушке.

- [ ] **Step 3: Обновить `task.md`**

Раздел «Формат ответа» и новый раздел «Как считаются баллы» — как в шаге 9 задачи 4, со своими числами: 10 тестов API, 5 Kafka, 5 Playwright. Убрать «основная», «дополнительная», «по желанию», «обязательная».

- [ ] **Step 4: Прогон пользователя на ВДИ и commit**

Попросить пользователя прогнать на ВДИ `pytest -q` и `pytest -q -n 4` в `participant\python` и прислать хвост вывода. В том же сообщении — отклонения от спецификации по 1д.

```bash
git add -A review-tasks/1d-python-review
git commit -m "feat: 1д — ключ по тестам, шаблон ответа и лист подсчёта в Excel

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 9: README и `rating-tasks.md`

**Files:**
- Modify: `review-tasks/README.md`
- Modify: `rating-tasks.md`

- [ ] **Step 1: Обновить `review-tasks/README.md`**

Найти описание 1а и 1д (`grep -n "1а\|1д\|дефект\|ловуш\|основн\|дополнительн" review-tasks/README.md`) и привести к новому виду: 20 тестов по 5 дефектов, 10 ловушек, +1 и −2, итог 0–100, шаблон ответа и лист подсчёта в Excel, исправленные версии в `jury/fixed/`. Убрать «основная/дополнительная часть». 1г не трогать.

- [ ] **Step 2: Обновить `rating-tasks.md`**

В «Открытые вопросы» добавить:

```markdown
- Задания-ревью 1а и 1д считаются по шкале 0–100, оценка собственных артефактов — 0–5. Как их сопоставить в общем рейтинге.
```

Если в документе есть упоминания подсчёта 1а или 1д по старой формуле — заменить.

- [ ] **Step 3: Финальная проверка ветки**

```bash
grep -rn "основная часть\|дополнительная часть\|по желанию" review-tasks/1a-autotest-review review-tasks/1d-python-review review-tasks/README.md
grep -rn "TK900218\|900218" review-tasks/1a-autotest-review review-tasks/README.md
cd review-tasks/tools && .venv/bin/pytest -q && .venv/bin/python build_sheets.py ../1a-autotest-review && .venv/bin/python build_sheets.py ../1d-python-review
```

Expected: первые два `grep` пустые (кроме упоминания объединения в ключе 1а), тесты скрипта `4 passed`, оба ключа проходят проверку.

- [ ] **Step 4: Commit**

```bash
git add review-tasks/README.md rating-tasks.md
git commit -m "docs: README и рейтинг — новый подсчёт 1а и 1д

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

После этого спросить пользователя, делать ли PR в `main`.
