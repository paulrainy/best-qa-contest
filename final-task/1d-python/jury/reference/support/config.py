from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StandConfig:
    http_url: str
    http_timeout_s: float
    amqp: dict
    database: dict


def load_config(path: Path) -> StandConfig:
    parser = ConfigParser()
    with Path(path).open(encoding="utf-8") as source:
        parser.read_file(source)
    return StandConfig(
        parser["http"]["base_url"], parser["http"].getfloat("timeout_s"),
        dict(host=parser["amqp"]["host"], port=parser["amqp"].getint("port"),
             virtual_host=parser["amqp"]["virtual_host"],
             username=parser["amqp"]["username"], password=parser["amqp"]["password"]),
        dict(host=parser["database"]["host"], port=parser["database"].getint("port"),
             dbname=parser["database"]["dbname"], user=parser["database"]["username"],
             password=parser["database"]["password"],
             connect_timeout=parser["database"].getint("connect_timeout_s")),
    )
