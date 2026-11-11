from types import SimpleNamespace

import pytest

from support.amqp import Events
from support.api import encode_json
from tests_support.test_polling import Clock


class Channel:
    is_open = True

    def __init__(self, events):
        self.messages = iter(events)
        self.queues = set()

    def queue_declare(self, **kwargs):
        self.queues.add("own-queue")
        return SimpleNamespace(method=SimpleNamespace(queue="own-queue"))

    def queue_bind(self, **kwargs):
        pass

    def basic_get(self, **kwargs):
        event = next(self.messages, None)
        if event is None:
            return None, None, None
        return SimpleNamespace(delivery_tag=1), None, encode_json(event).encode()

    def basic_ack(self, **kwargs):
        pass

    def queue_delete(self, queue):
        self.queues.remove(queue)


def test_foreign_message_cannot_satisfy_own_event_wait():
    clock = Clock()
    channel = Channel([
        {"transferId": "foreign", "eventType": "TransferCreated"},
        {"transferId": "own-id", "eventType": "TransferCompleted"},
        {"transferId": "own-id", "eventType": "TransferCreated", "amount": 100},
    ])
    with Events.subscribe(channel, "transfer.created") as events:
        result = events.wait("own-id", "TransferCreated",
                             monotonic=clock.monotonic, sleep=clock.sleep)
        assert result["amount"] == 100
    assert channel.queues == set()


def test_missing_message_has_bounded_timeout_and_queue_cleanup():
    clock = Clock()
    channel = Channel([])
    with pytest.raises(TimeoutError, match="own-id.*TransferCreated"):
        with Events.subscribe(channel, "transfer.created") as events:
            events.wait("own-id", "TransferCreated", timeout_s=0.1,
                        monotonic=clock.monotonic, sleep=clock.sleep)
    assert channel.queues == set()
