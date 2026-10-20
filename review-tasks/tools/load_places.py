"""Места в материале задания 1c: разбор места из ключа и список мест, которые есть в файле единицы.

Ключ места — строка вида `jmx:Thread Group → Вход`, `панель:RPS`, `переменная:host`, `дашборд`,
`строка:14`, `раздел:12.2`, `таблица:3`, `рисунок:2`, `шапка`, `название`.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

KINDS = {f'{n:02d}': kind for kind, numbers in [('jmx', range(1, 11)), ('protocol', range(11, 16)),
                                                ('json', range(16, 19)), ('sql', range(19, 21))]
         for n in numbers}

FILES = {'jmx': 'participant/scripts/{unit}-*.jmx', 'json': 'participant/monitoring/{unit}-*.json',
         'sql': 'participant/monitoring/{unit}-*.sql', 'protocol': 'jury/source/protocols/{unit}-*.md'}

JMX = re.compile(r'`([^`]+)`')
PANEL = re.compile(r'[Пп]анель «([^»]+)»')
VARIABLE = re.compile(r'[Пп]еременная \$?(\w+)')
DASHBOARD = re.compile(r'(?<!\w)Дашборд(?!\w)')
LINES = re.compile(r'[Сс]трок[аи] (\d+)(?:[–-](\d+))?')
PROTOCOL = re.compile(r'(Раздел|Таблица|Рисунок) (\d+(?:\.\d+)*)')
PROTOCOL_WORDS = {'Шапка': 'шапка', 'Название': 'название'}


def place_keys(kind: str, text: str) -> set:
    if kind == 'jmx':
        return {f'jmx:{path.strip()}' for path in JMX.findall(text)}
    if kind == 'json':
        keys = {f'панель:{title}' for title in PANEL.findall(text)}
        keys |= {f'переменная:{name}' for name in VARIABLE.findall(text)}
        return keys | ({'дашборд'} if DASHBOARD.search(text) else set())
    if kind == 'sql':
        return {f'строка:{n}' for start, end in LINES.findall(text) for n in range(int(start), int(end or start) + 1)}
    if kind == 'protocol':
        keys = {f'{what.lower()}:{number}' for what, number in PROTOCOL.findall(text)}
        return keys | {key for word, key in PROTOCOL_WORDS.items() if re.search(rf'(?<!\w){word}(?!\w)', text)}
    raise ValueError(kind)


def unit_files(task: Path) -> dict:
    found = {}
    for unit, kind in KINDS.items():
        files = sorted(task.glob(FILES[kind].format(unit=unit)))
        if len(files) > 1:
            sys.exit(f'у единицы {unit} несколько файлов: {", ".join(f.name for f in files)}')
        if files:
            found[unit] = files[0]
    return found


# ---------- .jmx ----------

def jmx_tree(path: Path) -> dict:
    """Путь в дереве → XML-элемент. Корень — «Test Plan», дальше имена через « → »."""
    root = ET.parse(path).getroot().find('hashTree')
    found = {}

    def walk(tree, prefix):
        children = list(tree)
        for element, sub in zip(children[::2], children[1::2]):
            name = element.get('testname')
            if prefix is None:
                found['Test Plan'] = element
                walk(sub, '')
            else:
                full = f'{prefix} → {name}' if prefix else name
                found[full] = element
                walk(sub, full)

    walk(root, None)
    return found


def jmx_props(element) -> list:
    """Непустые простые свойства элемента и вложенных свойств — то, что видно в его окне в GUI."""
    props = []
    for node in element.iter():
        if node.tag in ('stringProp', 'boolProp', 'intProp', 'longProp') and (node.text or '').strip():
            value = node.text.strip().replace('\n', '⏎')
            props.append(f'{node.get("name")}={value[:200]}')
        elif node.tag == 'doubleProp':
            props.append(f'{node.findtext("name")}={node.findtext("value")}')
    return props


# ---------- дашборд ----------

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8')), None
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return None, f'{path.name}: не разбирается: {error}'


def all_panels(panels) -> list:
    found = []
    for panel in panels or []:
        found.append(panel)
        found += all_panels(panel.get('panels'))
    return found


def check_dashboard(path: Path) -> list:
    data, error = load_json(path)
    if error:
        return [error]
    errors = [f'{path.name}: нет {key}' for key in ('title', 'uid', 'panels', 'schemaVersion') if key not in data]
    seen = set()
    for panel in all_panels(data.get('panels')):
        title = panel.get('title', '')
        if panel.get('id') in seen:
            errors.append(f'{path.name}: повтор id {panel.get("id")}')
        seen.add(panel.get('id'))
        for key in ('title', 'type', 'gridPos'):
            if key not in panel:
                errors.append(f'{path.name}: панель «{title}»: нет {key}')
        if panel.get('type') == 'row':
            continue
        if 'datasource' not in panel:
            errors.append(f'{path.name}: панель «{title}»: нет datasource')
        for target in panel.get('targets', []):
            if 'refId' not in target:
                errors.append(f'{path.name}: панель «{title}»: запрос без refId')
    return errors


def dashboard_targets(data) -> set:
    keys = {'дашборд'} | {f'панель:{p.get("title")}' for p in all_panels(data.get('panels'))}
    return keys | {f'переменная:{v.get("name")}' for v in data.get('templating', {}).get('list', [])}


QUERY_FIELDS = ('query', 'expr', 'rawSql')


def describe_target(target) -> str:
    for field in QUERY_FIELDS:
        if target.get(field):
            return f'{target.get("refId")}: {target[field]}'
    rest = {k: v for k, v in target.items() if k not in ('refId', 'datasource')}
    return f'{target.get("refId")}: {json.dumps(rest, ensure_ascii=False)}'


# ---------- общие ----------

@lru_cache(maxsize=None)
def _targets(kind: str, path: Path, stamp: float) -> frozenset:
    if kind == 'jmx':
        return frozenset(f'jmx:{p}' for p in jmx_tree(path))
    if kind == 'json':
        errors = check_dashboard(path)
        if errors:
            sys.exit('Дашборд не прошёл проверку:\n' + '\n'.join(errors))
        return frozenset(dashboard_targets(load_json(path)[0]))
    if kind == 'sql':
        lines = path.read_text(encoding='utf-8').splitlines()
        return frozenset(f'строка:{n}' for n, line in enumerate(lines, start=1) if line.strip())
    if kind == 'protocol':
        import build_protocols
        return frozenset(build_protocols.places(build_protocols.parse(path)))
    raise ValueError(kind)


def targets(kind: str, path: Path) -> set:
    return set(_targets(kind, path, path.stat().st_mtime))


def describe(kind: str, path: Path, key: str) -> str:
    """Что стоит в месте: для сверки ключа с материалом глазами (--show)."""
    what, _, value = key.partition(':')
    if kind == 'jmx':
        element = jmx_tree(path).get(value)
        if element is None:
            return '<нет места>'
        off = ' (выключен)' if element.get('enabled') == 'false' else ''
        return f'{element.tag}{off} | ' + '; '.join(jmx_props(element))
    if kind == 'json':
        data = load_json(path)[0]
        if what == 'панель':
            panel = next((p for p in all_panels(data.get('panels')) if p.get('title') == value), None)
            if panel is None:
                return '<нет места>'
            unit = panel.get('fieldConfig', {}).get('defaults', {}).get('unit', '')
            queries = ' / '.join(describe_target(t) for t in panel.get('targets', []))
            return f'{panel.get("type")} unit={unit} | {queries}'
        if what == 'переменная':
            variable = next((v for v in data.get('templating', {}).get('list', []) if v.get('name') == value), {})
            return json.dumps(variable, ensure_ascii=False)
        return json.dumps({k: data.get(k) for k in ('time', 'refresh', 'links')}, ensure_ascii=False)
    if kind == 'sql':
        lines = path.read_text(encoding='utf-8').splitlines()
        number = int(value)
        return lines[number - 1].strip() if number <= len(lines) else '<нет строки>'
    if kind == 'protocol':
        import build_protocols
        return build_protocols.places(build_protocols.parse(path)).get(key, '<нет места>')
    raise ValueError(kind)
