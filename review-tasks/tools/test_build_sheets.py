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
