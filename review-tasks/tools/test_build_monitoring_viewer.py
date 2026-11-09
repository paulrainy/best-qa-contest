"""Просмотрщик должен точно представлять исходники, а не менять задание."""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "1c-load-review"
GENERATOR = Path(__file__).with_name("build_monitoring_viewer.py")
FILES = ["16-jmeter-influxdb.json", "17-efr-api-prometheus.json",
         "18-servers-zabbix.json", "19-stand-prepare.sql", "20-artifacts-and-data.sql"]


def render(task=TASK):
    assert GENERATOR.exists(), "Генератор ещё не реализован"
    spec = importlib.util.spec_from_file_location("viewer", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_html(task)


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.ids = []
        self.resources = []
        self.scripts = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if "src" in attrs or tag == "link":
            self.resources.append(attrs)
        if tag == "script":
            self.scripts.append(attrs)

    def handle_data(self, data):
        self.text.append(data)


def payload(html):
    return json.loads(re.search(r'<script id="sources" type="application/json">(.*?)</script>', html, re.S)[1])


def test_embedded_sources_and_lines_match_originals():
    html = render()
    page = Page(html)
    data = payload(html)
    assert [item["name"] for item in data] == FILES
    for item in data:
        original = (TASK / "participant/3-monitoring" / item["name"]).read_bytes().decode("utf-8").replace("\r\n", "\n")
        assert item["source"] == original
        number = item["name"][:2]
        ids = [i for i in page.ids if i.startswith(f"line-{number}-")]
        assert ids == [f"line-{number}-{n}" for n in range(1, len(original.splitlines()) + 1)]
    assert len(page.ids) == len(set(page.ids))
    assert page.resources == []


@pytest.fixture
def task_copy(tmp_path):
    folder = tmp_path / "participant/3-monitoring"
    folder.mkdir(parents=True)
    for name in FILES:
        shutil.copyfile(TASK / "participant/3-monitoring" / name, folder / name)
    return tmp_path


def test_unknown_and_empty_properties_are_visible_and_html_is_inert(task_copy):
    path = task_copy / "participant/3-monitoring" / FILES[0]
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    dashboard["panels"][0]["extra"] = {
        "false": False, "null": None, "empty": "", "list": [], "object": {},
        "hostile": '</script><script src="https://example.invalid/attack.js"></script>',
    }
    path.write_text(json.dumps(dashboard, ensure_ascii=False), encoding="utf-8")
    html = render(task_copy)
    page = Page(html)
    visible = " ".join(page.text)
    for name in ["extra.false", "extra.null", "extra.empty", "extra.list", "extra.object", "extra.hostile"]:
        assert name in visible
    for value in ["false", "null", '""', "[]", "{}"]:
        assert value in visible
    assert page.resources == []
    assert len(page.scripts) == 2  # данные и логика просмотрщика
    assert json.loads(payload(html)[0]["source"])["panels"][0]["extra"] == dashboard["panels"][0]["extra"]


def test_generator_reads_only_five_participant_sources(task_copy):
    jury = task_copy / "jury"
    jury.mkdir()
    (jury / "answer-key.md").write_text("SECRET_JURY_793")
    (task_copy / "participant/3-monitoring/notes.txt").write_text("UNRELATED_948")
    html = render(task_copy)
    assert "SECRET_JURY_793" not in html
    assert "UNRELATED_948" not in html


def test_cli_check_detects_stale_source_without_writing(task_copy):
    assert GENERATOR.exists(), "Генератор ещё не реализован"
    def run(*args):
        return subprocess.run([sys.executable, str(GENERATOR), str(task_copy), *args], capture_output=True, text=True)
    assert run("--check").returncode == 1
    assert run().returncode == 0
    output = task_copy / "participant/3-monitoring/review.html"
    before = output.read_bytes()
    assert run("--check").returncode == 0
    sql = task_copy / "participant/3-monitoring/19-stand-prepare.sql"
    sql.write_bytes(sql.read_bytes() + b"\nSELECT '<tag>';\r\n")
    assert run("--check").returncode == 1
    assert output.read_bytes() == before
    assert run().returncode == 0
    assert output.read_bytes() != before
    assert run("--check").returncode == 0


def test_checked_in_viewer_is_current():
    assert (TASK / "participant/3-monitoring/review.html").read_text(encoding="utf-8") == render()


@pytest.mark.parametrize("eol", [b"\n", b"\r\n"])
def test_check_does_not_depend_on_checkout_line_endings(task_copy, eol):
    folder = task_copy / "participant/3-monitoring"
    def convert(path):
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", eol))
    for name in FILES:
        convert(folder / name)
    output = folder / "review.html"
    output.write_bytes(render(task_copy).encode("utf-8"))
    convert(output)  # как review.html после checkout с core.autocrlf
    assert b"\r" not in render(task_copy).encode("utf-8")
    result = subprocess.run([sys.executable, str(GENERATOR), str(task_copy), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
