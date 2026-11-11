import json
from contextlib import AbstractContextManager, contextmanager
from decimal import Decimal

import pika

from support.polling import wait_for


@contextmanager
def channel_connection(config):
    settings = config.amqp
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=settings["host"], port=settings["port"], virtual_host=settings["virtual_host"],
        credentials=pika.PlainCredentials(settings["username"], settings["password"]),
        socket_timeout=3, stack_timeout=5, blocked_connection_timeout=5, heartbeat=30))
    try:
        yield connection.channel()
    finally:
        if connection.is_open:
            connection.close()


class Events(AbstractContextManager):
    def __init__(self, channel, queue):
        self.channel = channel
        self.queue = queue

    @classmethod
    def subscribe(cls, channel, routing_key):
        result = channel.queue_declare(queue="", exclusive=True, auto_delete=True)
        events = cls(channel, result.method.queue)
        try:
            channel.queue_bind(queue=events.queue, exchange="transfers", routing_key=routing_key)
        except Exception:
            events.__exit__(None, None, None)
            raise
        return events

    def __exit__(self, *args):
        if self.channel.is_open:
            self.channel.queue_delete(queue=self.queue)

    def wait(self, transfer_id, event_type, timeout_s=10, **clock):
        def read():
            method, properties, payload = self.channel.basic_get(queue=self.queue, auto_ack=False)
            if method is None:
                return None
            event = json.loads(payload, parse_float=Decimal)
            self.channel.basic_ack(delivery_tag=method.delivery_tag)
            return event

        return wait_for(read,
                        lambda event: event is not None and event.get("transferId") == transfer_id
                        and event.get("eventType") == event_type,
                        f"Событие {transfer_id} {event_type}", timeout_s, **clock)
