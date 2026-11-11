import pytest
import pika

from support.amqp import Events, channel_connection
from support.data import global_scope, pair, unique_key
from support.db import Db
from support.polling import wait_final
from tests.checks import balances, clock, completed


def test_missing_event_timeout_names_own_transfer(channel):
    own_id = unique_key()
    with Events.subscribe(channel, "transfer.created") as events:
        with pytest.raises(TimeoutError, match=own_id + " TransferCreated"):
            events.wait(own_id, "TransferCreated", timeout_s=0.1)


def test_queue_bound_before_action_is_deleted_on_close(api, channel):
    source, destination = pair(api)
    with Events.subscribe(channel, "transfer.created") as events:
        queue = events.queue
        transfer = completed(api, source, destination, "100.00")
        assert events.wait(transfer["transferId"], "TransferCreated")["amount"] == 100
    probe = channel.connection.channel()
    with pytest.raises(pika.exceptions.ChannelClosedByBroker) as missing:
        probe.queue_declare(queue=queue, passive=True)
    assert missing.value.reply_code == 404


@pytest.mark.global_state
def test_scope_restores_after_exception_and_connections_close(global_stand, stand_config):
    api = global_stand
    with pytest.raises(ValueError, match="контрольная остановка"):
        with Db(stand_config) as database, channel_connection(stand_config) as channel, global_scope(api):
            clock(api, "2090-01-01T12:00:00+03:00")
            api.post("/api/test/consumers/accounting/pause")
            api.post("/api/test/consumers/notifications/pause")
            raise ValueError("контрольная остановка")
    assert database.connection.closed
    assert channel.connection.is_closed
    assert api.get("/api/test/clock")["shifted"] is False
    assert api.get("/api/test/consumers") == {"accounting": "RUNNING", "notifications": "RUNNING"}
    source, destination = pair(api)
    completed(api, source, destination, "100.00")
    balances(api, source, destination, "999900.00", "100.00")
