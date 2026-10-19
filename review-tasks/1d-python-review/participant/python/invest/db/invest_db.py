from retrying import retry

from framework.db.db_client import DbClient


class InvestDb(DbClient):
    """Запросы к БД сервиса брокерского обслуживания."""

    def get_client_by_login(self, login):
        return self.query('SELECT * FROM client WHERE login = ?', login, fetch_one=True)

    def get_agreements(self, client_id):
        return self.query('SELECT * FROM agreement WHERE client_id = ? ORDER BY id', client_id)

    def get_account(self, agreement_id):
        return self.query("SELECT * FROM account WHERE agreement_id = ? AND currency = 'RUB'", agreement_id,
                          fetch_one=True)

    @retry(wait_fixed=500, stop_max_delay=15000)
    def wait_order_status(self, order_id, status):
        """Ждёт, пока поручение перейдёт в нужный статус."""
        order = self.query('SELECT * FROM money_order WHERE id = ?', order_id, fetch_one=True)
        assert order['status'] == status, f"Поручение {order_id}: статус {order['status']}, ожидался {status}"
        return order

    def get_tax_reports(self, client_id):
        return self.query('SELECT * FROM tax_report WHERE client_id = ? ORDER BY id DESC', client_id)

    def get_tariff_history(self, client_id):
        return self.query('SELECT * FROM tariff_history WHERE client_id = ? ORDER BY id DESC', client_id)

    def delete_client(self, client_id):
        self.execute('DELETE FROM client WHERE id = ?', client_id)

    def get_orders(self, agreement_id):
        return self.query('SELECT * FROM money_order WHERE agreement_id = ? ORDER BY id', agreement_id)

    @retry(wait_fixed=500, stop_max_delay=15000)
    def wait_tax_report_status(self, report_id, status):
        """Ждёт, пока заявка на справку перейдёт в нужный статус."""
        report = self.query('SELECT * FROM tax_report WHERE id = ?', report_id, fetch_one=True)
        assert report['status'] == status, f"Справка {report_id}: статус {report['status']}, ожидался {status}"
        return report
