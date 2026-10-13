"""Шаги и метки отчёта: одновременно в Allure и в Test IT (через ссылку на кейс)."""
from contextlib import contextmanager

import allure


class Reporting:

    @staticmethod
    @contextmanager
    def step(title: str):
        with allure.step(title):
            yield

    @staticmethod
    def id(work_item_id: int):
        def decorator(func):
            func = allure.id(str(work_item_id))(func)
            return allure.link(f'https://testit.rshb.local/projects/invest/tests/{work_item_id}',
                               name=f'TK-{work_item_id}')(func)
        return decorator

    @staticmethod
    def title(text: str):
        return allure.title(text)

    @staticmethod
    def description(text: str):
        return allure.description(text)

    @staticmethod
    def epic(text: str):
        return allure.epic(text)

    @staticmethod
    def feature(text: str):
        return allure.feature(text)
