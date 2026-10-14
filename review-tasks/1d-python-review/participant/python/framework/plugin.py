"""Подключается из корневого conftest.py: поднимает песочницу перед прогоном, если тесты идут на неё."""
import logging

from framework.config import Config


def pytest_configure(config):
    if hasattr(config, 'workerinput') or config.option.collectonly:
        return  # при запуске с -n песочницу поднимает главный процесс pytest, а не каждый воркер
    if not Config.is_sandbox():
        return
    from sandbox import server
    if server.port_busy(Config.sandbox_port()):
        logging.getLogger('sandbox').info('Песочница уже запущена, тесты работают с ней')
        return
    server.start(Config.sandbox_port(), Config.db_path())
