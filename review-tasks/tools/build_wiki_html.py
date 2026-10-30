"""HTML-копии task.md для страниц EvaWiki.

Запуск: python build_wiki_html.py ../1a-autotest-review/participant/1-selenide/task.md [...]
Рядом с каждым task.md пишет task.html. Его содержимое вставляется в EvaWiki через кнопку
«Исходный код» в редакторе страницы.

Стили — только инлайн, как на странице конкурса: внешние CSS вики не принимает. Цвет текста
и фон задаются у каждого блока явно: иначе в тёмной теме вики текст наследует светлый цвет
и пропадает на светлых панелях. Эмодзи в заголовках — числовыми ссылками (&#128203;),
чтобы не сломались при копировании через буфер.

Понимает то подмножество Markdown, которое есть в task.md: заголовки #–###, абзацы,
маркированные и нумерованные списки с вложенностью, таблицы, блоки кода ```, **жирный**,
`код` и голые ссылки http(s)://.
"""
import html
import re
import sys
from pathlib import Path

GREEN_DARK = '#194d33'
TEXT = '#333333'

WRAP = (f'max-width: 880px; margin: 0 auto; padding: 0 16px; text-align: left; color: {TEXT}; '
        'font-size: 15px; line-height: 1.7;')
HERO = ('background: linear-gradient(135deg, #EAF8DD, #D9F3C9); border-radius: 18px; padding: 20px 22px; '
        f'margin-bottom: 28px; box-shadow: 0 6px 16px rgba(0,0,0,0.06); color: {GREEN_DARK};')
HERO_KICKER = f'margin: 0 0 6px; font-size: 13px; font-weight: 600; color: #2e7d32;'
HERO_TITLE = f'margin: 0; font-size: 24px; line-height: 1.3; color: {GREEN_DARK};'
# Заголовки разделов стоят на фоне самой вики: средний зелёный читается и в светлой, и в тёмной теме.
H2 = 'color: #2e7d32; margin: 28px 0 12px; font-size: 21px;'
CARD = ('background: #ffffff; border-radius: 14px; padding: 22px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); '
        f'margin-bottom: 22px; color: {TEXT};')
PANEL = ('background: #F7FFF1; border: 1px dashed #B9E3A3; border-radius: 12px; padding: 14px 16px; '
         f'margin: 0 0 14px; color: {TEXT};')
H3 = f'margin: 0 0 10px; font-size: 17px; color: {GREEN_DARK};'
P = f'margin: 0 0 10px; color: {TEXT};'
LIST = f'margin: 0 0 10px; padding-left: 22px; color: {TEXT};'
LI = f'margin: 2px 0; color: {TEXT};'
TABLE = 'width: 100%; border-collapse: collapse; margin: 4px 0 12px; font-size: 14px;'
TH = ('background: #A5DD88; color: #194d33; font-weight: 700; text-align: left; padding: 8px 10px; '
      'border: 1px solid #8CC96F;')
TD = f'background: #ffffff; color: {TEXT}; padding: 8px 10px; border: 1px solid #CFE8BF; vertical-align: top;'
CODE = ('background: #EEF7E8; color: #1f4d2b; padding: 1px 5px; border-radius: 4px; '
        "font-family: Consolas, 'Courier New', monospace; font-size: 0.92em;")
PRE = ('background: #263238; color: #E8F5E9; padding: 12px 14px; border-radius: 10px; margin: 6px 0 12px; '
       "overflow-x: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-family: Consolas, 'Courier New', "
       'monospace; font-size: 13px; line-height: 1.5;')
LINK = 'color: #1f6f2a; font-weight: 600;'
STRONG = f'color: {GREEN_DARK};'

ICONS = {
    'Что нужно сделать': 128203,      # 📋
    'Что ещё есть в проекте': 129513,  # 🧩
    'Стенды и БД': 128452,             # 🗄
    'Формат ответа': 128221,           # 📝
    'Как считаются баллы': 127919,     # 🎯
    'Как запустить тесты': 128640,     # 🚀
    'Тест-кейсы': 129514,              # 🧪
}
DEFAULT_ICON = 128204                  # 📌

KICKERS = {
    '1-selenide': 'Рейтинговое задание 1a · часть 1 из 3',
    '2-playwright': 'Рейтинговое задание 1a · часть 2 из 3',
    '3-sql': 'Рейтинговое задание 1a · часть 3 из 3',
}

LIST_RE = re.compile(r'^(\s*)([-*]|\d+\.)\s+(.*)$')
URL_RE = re.compile(r'https?://[^\s<]+')


def inline(text: str) -> str:
    """Экранирует текст и размечает `код`, **жирный** и голые ссылки."""
    codes = []

    def keep_code(m):
        # Короткий код не переносим посреди слова, длинные пути — можно.
        style = CODE + (' white-space: nowrap;' if len(m.group(1)) <= 40 else '')
        codes.append(f'<code style="{style}">{html.escape(m.group(1))}</code>')
        return f'\x00{len(codes) - 1}\x00'

    text = re.sub(r'`([^`]+)`', keep_code, text)
    text = html.escape(text, quote=False)
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: f'<strong style="{STRONG}">{m.group(1)}</strong>', text)

    def link(m):
        url = m.group(0)
        tail = ''
        while url and url[-1] in '.,;:)»':
            tail = url[-1] + tail
            url = url[:-1]
        return f'<a style="{LINK}" href="{url}" target="_blank">{url}</a>{tail}'

    text = URL_RE.sub(link, text)
    return re.sub(r'\x00(\d+)\x00', lambda m: codes[int(m.group(1))], text)


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(' '))


def parse_blocks(lines: list[str]) -> list[tuple]:
    """Делит строки на блоки: ('h', уровень, текст), ('p', текст), ('code', текст),
    ('table', строки), ('list', упорядоченный, пункты), где пункт — список блоков."""
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith('```'):
            base = indent_of(line)
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                body.append(lines[i][base:] if indent_of(lines[i]) >= base else lines[i].lstrip(' '))
                i += 1
            blocks.append(('code', '\n'.join(body)))
            i += 1
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            blocks.append(('h', len(m.group(1)), m.group(2)))
            i += 1
            continue
        if stripped.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i].strip())
                i += 1
            blocks.append(('table', rows))
            continue
        if LIST_RE.match(line):
            i = parse_list(lines, i, blocks)
            continue
        para = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not starts_block(lines[i]):
            para.append(lines[i].strip())
            i += 1
        blocks.append(('p', ' '.join(para)))
    return blocks


def starts_block(line: str) -> bool:
    s = line.strip()
    return s.startswith(('```', '|', '#')) or bool(LIST_RE.match(line))


def parse_list(lines: list[str], i: int, blocks: list) -> int:
    first = LIST_RE.match(lines[i])
    base = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    items = []
    while i < len(lines):
        m = LIST_RE.match(lines[i])
        if not m or len(m.group(1)) != base or m.group(2)[0].isdigit() != ordered:
            break
        content_indent = base + len(m.group(2)) + 1
        body = [m.group(3)]
        i += 1
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                nxt = next((l for l in lines[i + 1:] if l.strip()), None)
                if nxt is None or indent_of(nxt) < content_indent:
                    break
                body.append('')
            elif indent_of(line) >= content_indent:
                body.append(line[content_indent:])
            elif LIST_RE.match(line) and indent_of(line) > base:
                body.append(line.lstrip(' '))
            elif indent_of(line) <= base:
                break
            else:
                body.append(line.strip())
            i += 1
        items.append(parse_blocks(body))
        # Пустая строка между пунктами одного списка не разрывает список.
        j = i
        while j < len(lines) and not lines[j].strip():
            j += 1
        nxt = LIST_RE.match(lines[j]) if j < len(lines) else None
        if nxt and len(nxt.group(1)) == base and nxt.group(2)[0].isdigit() == ordered:
            i = j
    blocks.append(('list', ordered, items))
    return i


def render_table(rows: list[str]) -> str:
    def cells(row):
        return [c.strip() for c in row.strip().strip('|').split('|')]

    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    out = [f'<table style="{TABLE}"><thead><tr>']
    out += [f'<th style="{TH}">{inline(c)}</th>' for c in head]
    out.append('</tr></thead><tbody>')
    for r in body:
        out.append('<tr>' + ''.join(f'<td style="{TD}">{inline(c)}</td>' for c in r) + '</tr>')
    out.append('</tbody></table>')
    return ''.join(out)


def render(blocks: list[tuple], tight: bool = False) -> str:
    out = []
    for b in blocks:
        kind = b[0]
        if kind == 'p':
            out.append(inline(b[1]) if tight and len(blocks) == 1 else f'<p style="{P}">{inline(b[1])}</p>')
        elif kind == 'code':
            out.append(f'<pre style="{PRE}"><code>{html.escape(b[1])}</code></pre>')
        elif kind == 'table':
            out.append(render_table(b[1]))
        elif kind == 'list':
            tag = 'ol' if b[1] else 'ul'
            items = ''.join(f'<li style="{LI}">{render(item, tight=True)}</li>' for item in b[2])
            out.append(f'<{tag} style="{LIST}">{items}</{tag}>')
        elif kind == 'h':
            out.append(f'<h3 style="{H3}">{inline(b[2])}</h3>')
    return '\n'.join(out)


def split_by(blocks: list[tuple], level: int) -> tuple[list, list[tuple[str, list]]]:
    """Блоки до первого заголовка уровня level и пары (заголовок, блоки раздела)."""
    head, parts = [], []
    for b in blocks:
        if b[0] == 'h' and b[1] == level:
            parts.append((b[2], []))
        elif parts:
            parts[-1][1].append(b)
        else:
            head.append(b)
    return head, parts


def render_section(title: str, blocks: list[tuple]) -> str:
    icon = ICONS.get(title, DEFAULT_ICON)
    intro, subs = split_by(blocks, 3)
    inner = []
    if intro:
        inner.append(render(intro))
    for sub_title, sub_blocks in subs:
        inner.append(f'<div style="{PANEL}"><h3 style="{H3}">{inline(sub_title)}</h3>\n{render(sub_blocks)}</div>')
    return (f'<h2 style="{H2}">&#{icon};&nbsp;<b>{inline(title)}</b></h2>\n'
            f'<div style="{CARD}">\n' + '\n'.join(inner) + '\n</div>')


def build(md: str, kicker: str = '') -> str:
    blocks = parse_blocks(md.splitlines())
    head, sections = split_by(blocks, 2)
    title = next((b[2] for b in head if b[0] == 'h' and b[1] == 1), '')
    title = re.sub(r'^Задание:\s*', '', title)
    title = title[:1].upper() + title[1:]
    rest = [b for b in head if not (b[0] == 'h' and b[1] == 1)]
    out = [f'<div style="{WRAP}">', f'<div style="{HERO}">']
    if kicker:
        out.append(f'<p style="{HERO_KICKER}">{html.escape(kicker)}</p>')
    out.append(f'<h1 style="{HERO_TITLE}">{inline(title)}</h1>')
    out.append('</div>')
    if rest:
        out.append(f'<div style="{CARD}">{render(rest)}</div>')
    out += [render_section(t, b) for t, b in sections]
    out.append('</div>')
    return '\n'.join(out) + '\n'


def main(paths: list[str]) -> None:
    if not paths:
        sys.exit(__doc__)
    for p in map(Path, paths):
        target = p.with_suffix('.html')
        target.write_text(build(p.read_text(encoding='utf-8'), KICKERS.get(p.parent.name, '')), encoding='utf-8')
        print(target)


if __name__ == '__main__':
    main(sys.argv[1:])
