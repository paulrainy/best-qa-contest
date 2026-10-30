from pathlib import Path

import build_wiki_html as w

TASKS = Path(__file__).parent.parent / '1a-autotest-review' / 'participant'


def test_list_keeps_code_block_and_numbering():
    md = '1. Откройте папку.\n2. Запустите:\n\n   ```bash\n   mvn test\n   ```\n\n3. Готово.\n'
    blocks = w.parse_blocks(md.splitlines())
    assert len(blocks) == 1 and blocks[0][0] == 'list' and blocks[0][1] is True
    items = blocks[0][2]
    assert len(items) == 3
    assert ('code', 'mvn test') in items[1]


def test_nested_bullets_inside_ordered_item():
    md = '1. В папке:\n   - первый;\n   - второй.\n2. Дальше.\n'
    items = w.parse_blocks(md.splitlines())[0][2]
    assert len(items) == 2
    assert items[0][1][0] == 'list' and items[0][1][1] is False and len(items[0][1][2]) == 2


def test_inline_escapes_and_links():
    out = w.inline('Откройте http://localhost:18080/efr/. Поле `<a&b>` и **жирный**')
    assert 'href="http://localhost:18080/efr/"' in out
    assert '/efr/</a>.' in out
    assert '&lt;a&amp;b&gt;' in out
    assert '<strong' in out


def test_url_inside_code_is_not_linked():
    out = w.inline('`jdbc:h2:tcp://localhost:19092/mem:RTEST`')
    assert '<a ' not in out


def test_real_tasks_keep_all_test_cases():
    for folder, first, last in [('1-selenide', 900101, 900110), ('2-playwright', 900111, 900115),
                                ('3-sql', 900116, 900120)]:
        md = (TASKS / folder / 'task.md').read_text(encoding='utf-8')
        out = w.build(md, w.KICKERS[folder])
        for n in range(first, last + 1):
            assert f'TK-{n}' in out
        assert out.count('<table') == sum(1 for l in md.splitlines() if l.startswith('| --- |'))
        assert out.count('<pre') == md.count('```') // 2
        assert '**' not in out and '`' not in out
        assert not any(ord(c) >= 0x1F000 for c in out)  # эмодзи только числовыми ссылками

