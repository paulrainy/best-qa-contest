import random
from pathlib import Path

import pytest

from support.config import load_config


def pytest_addoption(parser):
    parser.addoption("--stand-config", default=str(Path(__file__).parent / "config/stand.ini"))
    parser.addoption("--http-log", default=None, help="Новый файл JSONL запросов и ответов")
    parser.addoption("--order-seed", type=int, default=None, help="Перемешать полный набор без исключения тестов")


def pytest_collection_modifyitems(config, items):
    seed = config.getoption("--order-seed")
    if seed is not None:
        random.Random(seed).shuffle(items)


@pytest.fixture(scope="session")
def stand_config(pytestconfig):
    return load_config(Path(pytestconfig.getoption("--stand-config")))
