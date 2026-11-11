from pathlib import Path

import pytest

from support.reporting import fresh_output


def test_existing_report_cannot_be_reused_as_a_fresh_run(tmp_path):
    old = tmp_path / "full.xml"
    old.write_text("<testsuite/>")
    with pytest.raises(ValueError, match="существует"):
        fresh_output(old)
    assert old.read_text() == "<testsuite/>"


def test_new_output_path_is_allowed_without_creating_a_fake_result(tmp_path):
    new = tmp_path / "new-run" / "full.xml"
    fresh_output(new)
    assert not new.exists()
