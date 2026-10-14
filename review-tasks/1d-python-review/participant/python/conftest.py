import pytest

from framework.browser import find_browser

pytest_plugins = ['framework.plugin']


@pytest.fixture(scope='session')
def browser_type_launch_args(browser_type_launch_args):
    """UI-тесты запускаются в браузере, установленном на компьютере, а не в скачанном Playwright."""
    return {**browser_type_launch_args, 'executable_path': find_browser()}
