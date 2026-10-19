"""Шаблон ответа участника и лист подсчёта из ключа задания.

Запуск: python build_sheets.py ../1a-autotest-review [--show]
Читает jury/answer-key.md, пишет participant/answer-template.xlsx и jury/scoring-sheet.xlsx.
Падает, если тестов не 20, в тесте не 5 дефектов, ловушек не 10 или дефект и ловушка указывают на одну строку.
--show печатает строки кода, на которые ссылается ключ, — для сверки глазами.
"""
import re
import sys
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

TESTS = 20
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
    if len(per_test) != TESTS:
        errors.append(f'тестов {len(per_test)}, нужно {TESTS}')
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


def plain(text: str) -> str:
    """Без разметки Markdown: в Excel обратные кавычки только мешают читать."""
    return text.replace('`', '')


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
    zero_one = DataValidation(type='whole', operator='between', formula1='0', formula2='1', allow_blank=True,
                              showErrorMessage=True, errorTitle='Только 0 или 1',
                              error='Поставьте 1, если засчитываем, или 0, если нет. Другие значения итог не учтёт.')
    sheet.add_data_validation(zero_one)
    row = 2
    for number, test, place, essence, accept in defects:
        for col, value in enumerate([number, test, place, essence, accept], start=1):
            sheet.cell(row=row, column=col, value=plain(value)).alignment = WRAP
        zero_one.add(sheet.cell(row=row, column=6))
        row += 1
    last_defect = row - 1
    row += 1
    for col, value in enumerate(['Ловушки', '', '', 'Почему код корректен',
                                 'Ставим 1, если участник предлагает «исправить» это место. '
                                 'Если сам объяснил, почему код верен, — 0. Каждая ловушка −2 балла'], start=1):
        cell = sheet.cell(row=row, column=col, value=value)
        cell.font, cell.alignment = HEADER, WRAP
    row += 1
    first_trap = row
    for number, place, hit, why in traps:
        for col, value in enumerate([number, '', place, why, hit], start=1):
            sheet.cell(row=row, column=col, value=plain(value)).alignment = WRAP
        zero_one.add(sheet.cell(row=row, column=6))
        row += 1
    last_trap = row - 1
    row += 2
    sheet.cell(row=row, column=5, value='Итог: max(0, дефекты − 2 × ловушки)').font = HEADER
    sheet.cell(row=row, column=6, value=f'=MAX(0,SUM(F2:F{last_defect})-2*SUM(F{first_trap}:F{last_trap}))').font = HEADER
    book.save(path)


def show(defects, traps, task: Path):
    skip = {'target', 'jury', '.m2', '.venv', 'build'}
    for row in defects + traps:
        cited = row[2] if row[0].startswith('Д') else row[1]
        for name, start, end in PLACE.findall(cited):
            files = sorted(p for p in task.rglob(name) if not skip & set(p.parts))
            if not files:
                print(f'{row[0]}: файл {name} не найден')
                continue
            for file in files:
                # Одно имя в нескольких песочницах (BaseTest.java) — печатаем каждую с путём.
                label = name if len(files) == 1 else str(file.relative_to(task))
                lines = file.read_text(encoding='utf-8').splitlines()
                for n in range(int(start), int(end or start) + 1):
                    print(f'{row[0]} {label}:{n}: {lines[n - 1].strip() if n <= len(lines) else "<нет строки>"}')


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
