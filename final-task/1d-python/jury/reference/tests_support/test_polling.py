import pytest

from support.polling import wait_final


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class TransferApi:
    def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.last = "PROCESSING"

    def get(self, path):
        assert path == "/api/v1/transfers/own-id"
        self.last = next(self.statuses, self.last)
        return {"transferId": "own-id", "status": self.last}


def test_wait_final_observes_completed_instead_of_returning_processing():
    clock = Clock()
    result = wait_final(TransferApi(["PROCESSING", "COMPLETED"]), "own-id",
                        monotonic=clock.monotonic, sleep=clock.sleep)
    assert result["status"] == "COMPLETED"


def test_wait_final_times_out_with_transfer_id():
    clock = Clock()
    with pytest.raises(TimeoutError, match="own-id.*PROCESSING"):
        wait_final(TransferApi(["PROCESSING"]), "own-id", timeout_s=0.2,
                   monotonic=clock.monotonic, sleep=clock.sleep)
    assert 0.2 <= clock.now <= 0.3
