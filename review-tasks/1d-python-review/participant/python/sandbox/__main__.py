"""Запуск песочницы отдельно от тестов: python -m sandbox"""
import logging
import threading

from framework.config import Config
from sandbox import server

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s - %(message)s')
    if server.port_busy(Config.sandbox_port()):
        raise SystemExit(f'Порт {Config.sandbox_port()} занят: песочница уже запущена или порт занят другой программой')
    server.start(Config.sandbox_port(), Config.db_path())
    print(f'Песочница запущена: {Config.api_url()}', flush=True)
    print(f'База данных SQLite: {Config.db_path()}', flush=True)
    print('Сотрудник бэк-офиса: bo_operator1 / Oper1#Playground', flush=True)
    print('Клиенты стенда: ivanova_ma, petrov_sv, smirnov_ap, kuznetsova_ei, volkov_dn, inv_client_lock — пароль Client#Playground', flush=True)
    print('Остановить — Ctrl+C', flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
