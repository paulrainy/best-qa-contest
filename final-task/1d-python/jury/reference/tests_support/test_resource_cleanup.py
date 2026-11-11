import pytest

from support.data import global_scope


class StandState:
    def __init__(self):
        self.shifted = False
        self.states = {"accounting": "RUNNING", "notifications": "RUNNING"}
        self.fail_resume = False

    def delete(self, path):
        assert path == "/api/test/clock"
        self.shifted = False

    def post(self, path):
        name = path.split("/")[-2]
        if self.fail_resume and name == "accounting":
            raise RuntimeError("accounting unavailable")
        self.states[name] = "RUNNING"


def test_exception_restores_clock_and_both_consumers():
    stand = StandState()
    with pytest.raises(ValueError, match="scenario failure"):
        with global_scope(stand):
            stand.shifted = True
            stand.states = {"accounting": "PAUSED", "notifications": "PAUSED"}
            raise ValueError("scenario failure")
    assert stand.shifted is False
    assert stand.states == {"accounting": "RUNNING", "notifications": "RUNNING"}


def test_cleanup_attempts_remaining_actions_after_resume_failure():
    stand = StandState()
    with pytest.raises(ExceptionGroup, match="восстановление"):
        with global_scope(stand):
            stand.shifted = True
            stand.states = {"accounting": "PAUSED", "notifications": "PAUSED"}
            stand.fail_resume = True
    assert stand.shifted is False
    assert stand.states["notifications"] == "RUNNING"
