from playwright.sync_api import Locator, Page, expect


class LoginPage:

    def __init__(self, page: Page):
        self.page = page

    def login(self, login, password):
        self.page.get_by_label('Логин').fill(login)
        self.page.get_by_label('Пароль').fill(password)
        self.page.get_by_role('button', name='Войти').click()
        expect(self.page.get_by_role('heading', name='Мои договоры')).to_be_visible()


class AgreementsPage:

    def __init__(self, page: Page):
        self.page = page

    def row(self, number) -> Locator:
        return self.page.get_by_test_id('agreement-row').filter(has_text=number)

    def open_agreement(self, number):
        self.row(number).get_by_role('link', name=number).click()
        expect(self.page.get_by_role('heading', name=f'Договор {number}')).to_be_visible()
        return AgreementPage(self.page)


class AgreementPage:

    def __init__(self, page: Page):
        self.page = page

    def balance_locator(self) -> Locator:
        return self.page.get_by_test_id('agreement-balance')

    def order_rows(self) -> Locator:
        return self.page.get_by_test_id('order-row')

    def refill(self, amount):
        self.page.get_by_role('button', name='Пополнить').click()
        self.page.get_by_label('Сумма, ₽').fill(str(amount))
        self.page.get_by_role('button', name='Создать поручение').click()

    def withdraw(self, amount):
        self.page.get_by_role('button', name='Вывести').click()
        self.page.get_by_label('Сумма, ₽').fill(str(amount))
        self.page.get_by_role('button', name='Создать поручение').click()


class TaxReportsPage:

    def __init__(self, page: Page):
        self.page = page

    def open(self):
        self.page.get_by_role('link', name='Справки').click()
        expect(self.page.get_by_role('heading', name='Справки НДФЛ')).to_be_visible()
        return self

    def order(self, year):
        self.page.get_by_label('Год').select_option(str(year))
        self.page.get_by_role('button', name='Заказать справку').click()

    def report_rows(self) -> Locator:
        return self.page.get_by_test_id('tax-report-row')


class ProfilePage:

    def __init__(self, page: Page):
        self.page = page

    def open(self):
        self.page.get_by_role('link', name='Профиль').click()
        expect(self.page.get_by_role('heading', name='Профиль')).to_be_visible()
        return self

    def tariff(self) -> Locator:
        return self.page.get_by_test_id('profile-tariff')

    def switch_tariff_button(self) -> Locator:
        return self.page.get_by_role('button', name='Перейти на тариф')
