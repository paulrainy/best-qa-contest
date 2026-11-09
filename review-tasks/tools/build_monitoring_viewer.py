#!/usr/bin/env python3
"""Собрать автономный просмотрщик пяти исходников мониторинга участника."""
import argparse
from html import escape
import json
from pathlib import Path
import re


ASSETS = Path(__file__).resolve().parents[1] / "1c-load-review/jury/source/monitoring/viewer"
FILES = (
    ("16-jmeter-influxdb.json", "JMeter / InfluxDB"),
    ("17-efr-api-prometheus.json", "API / Prometheus"),
    ("18-servers-zabbix.json", "Серверы / Zabbix"),
    ("19-stand-prepare.sql", "Подготовка стенда"),
    ("20-artifacts-and-data.sql", "Артефакты и данные"),
)
# Подсветка не разбирает и не исполняет SQL. В том числе сохраняет многострочные комментарии.
SQL_TOKEN = re.compile(
    r"(?P<comment>--[^\r\n]*|/\*[\s\S]*?\*/)"
    r"|(?P<string>'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\")"
    r"|(?P<keyword>\b(?:SELECT|FROM|WHERE|AS|WITH|VALUES|JOIN|LEFT|RIGHT|INNER|OUTER|"
    r"ON|USING|GROUP|ORDER|BY|AND|OR|NOT|IN|IS|NULL|SET|ALTER|TABLE|VACUUM|FULL|"
    r"ANALYZE|FILTER|BETWEEN|DISTINCT|LIMIT|UNION|ALL|CASE|WHEN|THEN|ELSE|END|INTERVAL)\b)",
    re.IGNORECASE,
)


def value_text(value):
    """Строки без JSON-кавычек удобны для чтения; пустая строка обозначается явно."""
    if isinstance(value, str) and value:
        return value
    return json.dumps(value, ensure_ascii=False)


def properties(value, prefix=""):
    """Все листья, включая пустые контейнеры: новые свойства не пропадают из UI."""
    if isinstance(value, dict) and value:
        for key, child in value.items():
            yield from properties(child, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from properties(child, f"{prefix}[{index}]")
    else:
        yield prefix, value_text(value)


def property_table(value):
    rows = "".join(
        f'<tr><th scope="row"><code>{escape(key)}</code></th>'
        f'<td><pre>{escape(text)}</pre></td></tr>'
        for key, text in properties(value)
    )
    return '<table class="properties"><thead><tr><th>Свойство</th><th>Значение</th></tr></thead><tbody>' + rows + '</tbody></table>'


def source_html(source, number, sql):
    # Сначала подсвечиваем целый текст, затем делим на строки: сохраняем состояние комментариев.
    parts = []
    pos = 0
    for match in SQL_TOKEN.finditer(source) if sql else ():
        parts.append(escape(source[pos:match.start()]))
        # Закрываем span перед переводом строки, чтобы строки были независимыми элементами.
        parts.append("\n".join(
            f'<span class="sql-{match.lastgroup}">{escape(line)}</span>'
            for line in match.group().replace("\r\n", "\n").replace("\r", "\n").split("\n")
        ))
        pos = match.end()
    parts.append(escape(source[pos:]))
    lines = "".join(parts).splitlines()
    return '<div class="source" aria-label="Исходник с номерами строк">' + "".join(
        f'<div class="source-line" id="line-{number}-{n}">'
        f'<a class="line-number" href="#line-{number}-{n}" aria-label="Строка {n}">{n}</a>'
        f'<code>{line}</code></div>' for n, line in enumerate(lines, 1)
    ) + '</div>'


def dashboard_views(data):
    panels = []
    for panel in data.get("panels", []):
        title = escape(str(panel.get("title", "Без названия")))
        panel_id = escape(str(panel.get("id", "не задан")))
        targets = panel.get("targets", [])
        queries = "".join(
            f'<h4>Запрос {escape(str(target.get("refId", index + 1)))}</h4>'
            + property_table(target) for index, target in enumerate(targets)
        )
        settings = {key: value for key, value in panel.items() if key != "targets"}
        panels.append(
            f'<details class="panel"><summary>{title} <span class="badge">ID {panel_id}</span></summary>'
            f'<div class="panel-body"><h3>Запросы</h3>{queries or "<p>Запросов нет.</p>"}'
            f'<h3>Настройки панели</h3>{property_table(settings)}</div></details>'
        )
    variables = data.get("templating", {})
    general = {key: value for key, value in data.items() if key not in ("panels", "templating")}
    return (
        '<div data-view="panels"><h2>Панели <span class="badge">' + str(len(panels)) + '</span></h2>'
        '<div class="expand-controls enhanced-only"><button type="button" data-expand="true">Раскрыть все</button>'
        '<button type="button" data-expand="false">Свернуть все</button></div>'
        + ("".join(panels) or '<p>Панелей нет.</p>') + '</div>'
        '<div data-view="variables"><h2>Переменные</h2>' + property_table(variables) + '</div>'
        '<div data-view="settings"><h2>Настройки дашборда</h2>' + property_table(general) + '</div>'
    )


def build_html(task_dir: Path) -> str:
    directory = task_dir / "participant/3-monitoring"
    sections, navigation, sources = [], [], []
    for name, label in FILES:
        # Git на Windows (core.autocrlf) отдаёт файлы с CRLF; страница не должна зависеть от чекаута.
        source = (directory / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
        number = name[:2]
        sql = name.endswith(".sql")
        data = None if sql else json.loads(source)
        sources.append({"name": name, "source": source})
        navigation.append(
            f'<a href="#task-{number}" data-task="{number}"><span class="nav-number">{number}</span>'
            f'<span>{label}<small>{"SQL · PostgreSQL" if sql else "JSON · Grafana"}</small></span></a>'
        )
        tabs = [] if sql else [("panels", "Панели"), ("variables", "Переменные"), ("settings", "Настройки")]
        tabs.append(("source", "Исходник"))
        buttons = "".join(f'<button type="button" data-tab="{key}" aria-pressed="false">{label}</button>' for key, label in tabs)
        sections.append(
            f'<section class="task" id="task-{number}" data-number="{number}">'
            f'<header><p class="eyebrow">Задание {number} / {"SQL" if sql else "Дашборд"}</p>'
            f'<h1 tabindex="-1">{escape(label)}</h1><p class="filename">{name}</p>'
            + (f'<p>{escape(data.get("title", ""))}</p>' if data is not None else '')
            + f'</header><div class="tabs enhanced-only" role="group" aria-label="Представление задания {number}">{buttons}</div>'
            + (dashboard_views(data) if data is not None else '')
            + f'<div data-view="source"><div class="source-toolbar"><h2>Исходник</h2>'
            f'<button class="enhanced-only" type="button" data-copy="{number}">Копировать файл</button></div>'
            + source_html(source, number, sql) + '</div></section>'
        )
    replacements = {
        "STYLE": (ASSETS / "viewer.css").read_text(encoding="utf-8"),
        "SCRIPT": (ASSETS / "viewer.js").read_text(encoding="utf-8"),
        "NAVIGATION": "".join(navigation),
        "SECTIONS": "".join(sections),
        # В JSON script HTML-сущности не декодируются. Unicode escape блокирует </script>.
        "SOURCES": json.dumps(sources, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"),
    }
    template = (ASSETS / "page.html").read_text(encoding="utf-8")
    return re.sub(r"@@([A-Z]+)@@", lambda match: replacements[match[1]], template)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=Path, help="Папка задания 1c-load-review")
    parser.add_argument("--check", action="store_true", help="Проверить актуальность, не записывая файл")
    args = parser.parse_args()
    try:
        html = build_html(args.task).encode("utf-8")
        output = args.task / "participant/3-monitoring/review.html"
        if args.check:
            # Собранная страница без CR; review.html в Windows-чекауте может быть с CRLF.
            if not output.exists() or output.read_bytes().replace(b"\r\n", b"\n") != html:
                print("review.html отсутствует или устарел. Выполните сборку без --check.")
                return 1
            print("review.html актуален.")
        else:
            output.write_bytes(html)
            print(f"Собран {output} ({len(html):,} байт).")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Ошибка сборки: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
