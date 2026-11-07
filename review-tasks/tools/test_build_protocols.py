from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytest
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

import build_protocols as bp

SOURCE = '''> УТВЕРЖДАЮ
> Руководитель ЦК НТ
# Протокол нагрузочного тестирования системы ЕФР

## 1. Сроки
С 01.11.2026 по 12.11.2026.

## 2. Результаты
Текст с **жирным** словом.

### 2.1 Поиск максимума
Таблица 1. Бизнес-метрики
| Операция | p95, мс | Порог, мс | Ошибки | Итог |
| --- | --- | --- | --- | --- |
| ОП-01 | 640 | 800 | 0,1 % | **ок** |
| ОП-02 | 910 | 1 000 | 0,2 % | ок |

Таблица 2. Утилизация
| Сервер | CPU |
| --- | --- |
| efr-nt-app01 | 45 % |

![Рисунок 1. Интенсивность](img/x.png)

- первый пункт
- второй пункт
'''


def picture(path: Path, color='C0'):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(2, 1))
    ax.plot([0, 1], [0, 1], color=color)
    fig.savefig(path)
    plt.close(fig)


def source(tmp_path: Path, text=SOURCE, image=True) -> Path:
    path = tmp_path / '11-max.md'
    path.write_text(text, encoding='utf-8')
    if image:
        picture(tmp_path / 'img' / 'x.png')
    return path


def test_parse_places(tmp_path):
    places = bp.places(bp.parse(source(tmp_path)))
    assert set(places) == {'шапка', 'название', 'раздел:1', 'раздел:2', 'раздел:2.1', 'таблица:1', 'таблица:2',
                           'рисунок:1'}
    assert places['раздел:2.1'] == '2.1 Поиск максимума'
    assert places['таблица:2'] == 'Таблица 2. Утилизация'


@pytest.mark.parametrize('old, new, image, message', [
    ('Таблица 2. Утилизация', 'Таблица 3. Утилизация', True, 'Таблица 3 после Таблица 1'),
    (None, None, False, 'нет файла img/x.png'),
    ('| ОП-02 | 910 | 1 000 | 0,2 % | ок |', '| ОП-02 | 910 | 1 000 | ок |', True,
     'Таблица 1: строка 2 — 4 колонки, нужно 5'),
    ('## 2. Результаты', '## 3. Результаты', True, 'раздел 3 после 1'),
    ('### 2.1 Поиск максимума', '### 2.2 Поиск максимума', True, 'раздел 2.2 после 2'),
    ('Таблица 2. Утилизация\n', '', True, 'таблица без подписи'),
    ('![Рисунок 1. Интенсивность]', '![Рисунок 2. Интенсивность]', True, 'Рисунок 2 после начала'),
])
def test_rejects(tmp_path, old, new, image, message):
    text = SOURCE.replace(old, new) if old else SOURCE
    with pytest.raises(SystemExit, match=message):
        bp.parse(source(tmp_path, text, image))


def test_write_docx(tmp_path):
    md = source(tmp_path)
    out = tmp_path / 'out.docx'
    bp.write(bp.parse(md), md, out)
    doc = Document(out)
    heading = next(p for p in doc.paragraphs if p.text == '2.1 Поиск максимума')
    assert heading.style.name == 'Heading 3'
    assert len(doc.tables) == 2
    assert doc.tables[0].cell(0, 1).text == 'p95, мс'
    assert len(doc.inline_shapes) == 1
    assert doc.core_properties.identifier == bp.source_hash(md)
    header = next(p for p in doc.paragraphs if p.text == 'УТВЕРЖДАЮ')
    assert header.alignment == WD_ALIGN_PARAGRAPH.RIGHT
    para = next(p for p in doc.paragraphs if p.text == 'Текст с жирным словом.')
    assert [r.bold for r in para.runs if r.text == 'жирным'] == [True]
    cell = doc.tables[0].cell(1, 4).paragraphs[0]
    assert [r.bold for r in cell.runs] == [True]
    assert [p.style.name for p in doc.paragraphs if p.text.endswith('пункт')] == ['List Bullet', 'List Bullet']


def test_hash_ignores_line_endings(tmp_path):
    """core.autocrlf на Windows выгружает исходник с CRLF — документ от этого не устаревает."""
    md = source(tmp_path)
    before = bp.source_hash(md)
    md.write_bytes(md.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    assert b'\r\n' in md.read_bytes()
    assert bp.source_hash(md) == before


def test_page_is_a4_and_picture_fits_text(tmp_path):
    md = source(tmp_path)
    out = tmp_path / 'out.docx'
    bp.write(bp.parse(md), md, out)
    doc = Document(out)
    section = doc.sections[0]
    assert (round(section.page_width.cm, 1), round(section.page_height.cm, 1)) == (21.0, 29.7)
    text_width = section.page_width - section.left_margin - section.right_margin
    assert doc.inline_shapes[0].width <= text_width


def test_table_columns_fit_longest_word(tmp_path):
    md = source(tmp_path)
    out = tmp_path / 'out.docx'
    bp.write(bp.parse(md), md, out)
    doc = Document(out)
    section = doc.sections[0]
    text_width = (section.page_width - section.left_margin - section.right_margin) / 360000  # EMU → см
    for table in doc.tables:
        widths = [cell.width.cm for cell in table.rows[0].cells]
        assert sum(widths) == pytest.approx(text_width, abs=0.05)
        assert [column.width.cm for column in table.columns] == pytest.approx(widths, abs=0.01)
    first = doc.tables[0].rows[0].cells
    assert first[0].width.cm >= len('Операция') * bp.CHAR + bp.PADDING  # заголовок не рвётся посреди слова
    assert first[2].width.cm >= len('1 000') * bp.DIGIT + bp.PADDING  # число не переносится по пробелу
    assert first[3].width.cm >= bp.token_width('0,1 %') + bp.PADDING  # «0,1 %» — одно целое, со знаком процента


def test_hash_changes_with_image(tmp_path):
    md = source(tmp_path)
    before = bp.source_hash(md)
    picture(tmp_path / 'img' / 'x.png', color='C3')
    assert bp.source_hash(md) != before


def test_build_writes_participant_docx(tmp_path):
    task = tmp_path / 'task'
    folder = task / 'jury' / 'source' / 'protocols'
    folder.mkdir(parents=True)
    source(folder)
    bp.build(task)
    assert (task / 'participant' / '2-protocols' / '11-max.docx').exists()


def test_build_skips_up_to_date(tmp_path):
    task = tmp_path / 'task'
    folder = task / 'jury' / 'source' / 'protocols'
    folder.mkdir(parents=True)
    source(folder)
    bp.build(task)
    out = task / 'participant' / '2-protocols' / '11-max.docx'
    before = out.read_bytes()
    assert bp.build(task) == []
    assert out.read_bytes() == before
