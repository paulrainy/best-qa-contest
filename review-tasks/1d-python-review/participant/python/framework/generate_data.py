"""Генерация тестовых данных: уникальные логины, ФИО, телефоны."""
import random
import uuid

LAST_NAMES = ['Орлов', 'Белов', 'Зайцев', 'Морозов', 'Лебедев', 'Козлов', 'Новиков', 'Егоров']
FIRST_NAMES = ['Андрей', 'Павел', 'Максим', 'Олег', 'Никита', 'Роман', 'Артём', 'Денис']
MIDDLE_NAMES = ['Ильич', 'Петрович', 'Сергеевич', 'Олегович', 'Юрьевич', 'Антонович']


class GenerateData:

    @staticmethod
    def login() -> str:
        return f'autotest_{uuid.uuid4().hex[:10]}'

    @staticmethod
    def password() -> str:
        return f'At#{uuid.uuid4().hex[:12]}'

    @staticmethod
    def phone() -> str:
        return '+79' + ''.join(random.choice('0123456789') for _ in range(9))

    def client(self) -> dict:
        return {
            'login': self.login(),
            'password': self.password(),
            'lastName': random.choice(LAST_NAMES),
            'firstName': random.choice(FIRST_NAMES),
            'middleName': random.choice(MIDDLE_NAMES),
            'phone': self.phone(),
        }
