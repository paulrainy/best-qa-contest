"""Настройки стенда. Всё берётся из переменных окружения, по умолчанию — песочница."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANDBOX_PORT = 18300


class Config:

    @staticmethod
    def sandbox_port() -> int:
        return int(os.getenv('INVEST_SANDBOX_PORT', SANDBOX_PORT))

    @staticmethod
    def api_url() -> str:
        return os.getenv('INVEST_API_URL', f'http://localhost:{Config.sandbox_port()}')

    @staticmethod
    def db_path() -> Path:
        return Path(os.getenv('INVEST_DB_PATH', ROOT / 'build' / 'invest.db'))

    @staticmethod
    def qa_service_url() -> str:
        return os.getenv('QA_SERVICE_URL', f'{Config.api_url()}/qa-service')

    @staticmethod
    def kafka_cluster() -> str:
        return os.getenv('KAFKA_CLUSTER_ID', 'invest-kafka')

    @staticmethod
    def is_sandbox() -> bool:
        return 'INVEST_API_URL' not in os.environ

    @staticmethod
    def user(role: str) -> tuple:
        """Логин и пароль служебной учётной записи: INVEST_USER_<РОЛЬ>_LOGIN / _PASSWORD."""
        defaults = {'BACKOFFICE': ('bo_operator1', 'Oper1#Playground')}
        login, password = defaults.get(role.upper(), (None, None))
        return (os.getenv(f'INVEST_USER_{role.upper()}_LOGIN', login),
                os.getenv(f'INVEST_USER_{role.upper()}_PASSWORD', password))
