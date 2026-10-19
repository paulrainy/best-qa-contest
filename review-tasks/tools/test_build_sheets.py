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
    validation, = sheet.data_validations.dataValidation
    assert validation.showErrorMessage
    assert validation.error


@pytest.mark.parametrize('kwargs, message', [
    ({'defects_per_test': 4}, 'TK900101: 4 дефекта'),
    ({'traps': 9}, 'ловушек 9'),
    ({'tests': 19}, 'тестов 19'),
    ({'clash': True}, 'TK900101Test.java:10'),
])
def test_rejects_broken_key(tmp_path, kwargs, message):
    task = make_task(tmp_path, **kwargs)
    with pytest.raises(SystemExit, match=message):
        build_sheets.build(task)


# ---------- Задание 1б: место вида «Шаг N» ----------

import build_testcases


def make_case_task(tmp_path: Path, place=None, defects_of_first=5, shared_first=False) -> Path:
    (tmp_path / 'jury').mkdir()
    (tmp_path / 'participant').mkdir()
    lines = ['| № | Кейс | Место | Категория | Суть | Засчитываем, если… |', '| --- | --- | --- | --- | --- | --- |']
    for t in range(1, 21):
        for d in range(1, (defects_of_first if t == 1 else 5) + 1):
            where = place if place and t == 1 and d == 1 else f'Шаг {d}, ожидаемый результат'
            lines.append(f'| Д4{t:02d}.{d} | 9004{t:02d} | {where} | BIQ | суть | признак |')
    lines += ['', '| № | Где | Попадание | Почему верно |', '| --- | --- | --- | --- |']
    lines += [f'| Л{n} | 9004{n:02d} Шаг 6 | замечание | потому что |' for n in range(1, 11)]
    (tmp_path / 'jury' / 'answer-key.md').write_text('\n'.join(lines), encoding='utf-8')
    steps = '\n'.join(f'- Шаг {n}\n  = Результат {n}' for n in range(1, 7))
    source = ['# 900901 Общий шаг\nРасположение: РТ_ЕФР -> Общие шаги\n\n## Шаги\n- Войти\n  = Вошли\n']
    for t in range(1, 21):
        own = steps.replace('- Шаг 1\n  = Результат 1', '- @900901') if shared_first and t == 1 else steps
        source.append(f'# 9004{t:02d} Кейс\nРасположение: BIQ\n\n## Шаги\n{own}\n')
    src = tmp_path / 'testcases.md'
    src.write_text('\n'.join(source), encoding='utf-8')
    cases = build_testcases.expand(build_testcases.parse(src))
    build_testcases.write(cases, tmp_path / 'participant' / 'testcases.xlsx')
    return tmp_path


def test_builds_case_sheets(tmp_path):
    task = make_case_task(tmp_path)
    build_sheets.build(task)

    template = load_workbook(task / 'participant' / 'answer-template.xlsx').active
    assert [template['A1'].value, template['B1'].value, template['A2'].value] == ['Кейс', 'Место', '900401']
    assert template.cell(row=101, column=1).value == '900420'

    sheet = load_workbook(task / 'jury' / 'scoring-sheet.xlsx').active
    assert sheet['D1'].value == 'Категория'
    assert sheet['A2'].value == 'Д401.1'
    assert sheet['D2'].value == 'BIQ'
    assert sheet['A104'].value == 'Л1'
    assert sheet['G116'].value == '=MAX(0,SUM(G2:G101)-2*SUM(G104:G113))'


@pytest.mark.parametrize('kwargs, message', [
    ({'place': 'Шаг 6'}, 'Л1 и дефект в одном месте: 900401 Шаг 6'),
    ({'place': 'Шаг 9'}, 'Д401.1: в кейсе 900401 нет элемента Шаг 9'),
    ({'place': 'где-то в середине'}, 'Д401.1: не понял место «где-то в середине»'),
    ({'shared_first': True}, r'Д401.1: дефект в общем шаге \(900401 Шаг 1\)'),
    ({'defects_of_first': 4}, '900401: 4 дефекта'),
])
def test_rejects_broken_case_key(tmp_path, kwargs, message):
    task = make_case_task(tmp_path, **kwargs)
    with pytest.raises(SystemExit, match=message):
        build_sheets.build(task)


def test_whole_section_place_is_allowed(tmp_path):
    build_sheets.build(make_case_task(tmp_path, place='Предусловия — нет клиента'))


def test_place_may_name_other_case():
    assert build_sheets.case_places('900401', 'Шаг 2; 900410 Предусловие 1') == {'900401 Шаг 2', '900410 Предусловие 1'}


def test_show_prints_case_element(tmp_path, capsys):
    task = make_case_task(tmp_path)
    build_sheets.show(*build_sheets.parse_key(task / 'jury' / 'answer-key.md'), task)
    out = capsys.readouterr().out
    assert 'Д401.1 900401 Шаг 1: Шаг 1 | ОР: Результат 1' in out
    assert 'Л1 900401 Шаг 6: Шаг 6 | ОР: Результат 6' in out
