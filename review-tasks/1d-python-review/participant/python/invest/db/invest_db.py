from retrying import retry

from framework.db.db_client import DbClient


class InvestDb(DbClient):
    """Запросы к БД сервиса брокерского обслуживания."""

    def get_client_by_login(self, login):
        return self.query(f"SELECT * FROM client WHERE login = '{login}'", fetch_one=True)

    def get_agreements(self, client_id):
        return self.query('SELECT * FROM agreement WHERE client_id = ? ORDER BY id', client_id)

    def get_account(self, agreement_id):
        return self.query("SELECT * FROM account WHERE agreement_id = ? AND currency = 'RUB'", agreement_id,
                          fetch_one=True)

    @retry(wait_fixed=500, stop_max_delay=15000)
    def wait_order_status(self, order_id, status):
        """Ждёт, пока поручение перейдёт в нужный статус."""
        order = self.query('SELECT * FROM money_order WHERE id = ?', order_id, fetch_one=True)
        assert order['status'] == status
        return order

    def get_last_order(self, order_type):
        return self.query('SELECT * FROM money_order WHERE type = ? ORDER BY created_at DESC LIMIT 1', order_type,
                          fetch_one=True)

    def count_executed_orders(self):
        return self.query("SELECT COUNT(*) AS cnt FROM money_order WHERE status = 'EXECUTED'", fetch_one=True)['cnt']

    def count_today_orders(self, agreement_id):
        return self.query("SELECT COUNT(*) AS cnt FROM money_order WHERE agreement_id = ? AND created_at = date('now')",
                          agreement_id, fetch_one=True)['cnt']

    def get_today_tax_reports(self, client_id):
        return self.query("SELECT * FROM tax_report WHERE client_id = ? AND date(registered_at) = date('now')"
                          ' ORDER BY id DESC', client_id)

    def get_tariff_history(self, client_id):
        return self.query('SELECT * FROM tariff_history WHERE client_id = ? ORDER BY id DESC', client_id)

    def set_balance(self, agreement_id, balance):
        """Подготовить остаток на счёте, не дожидаясь исполнения пополнения."""
        self.execute('UPDATE account SET balance = ? WHERE agreement_id = ?', balance, agreement_id)

    def delete_autotest_clients(self):
        self.execute("DELETE FROM client WHERE login LIKE 'autotest%'")

    def get_orders(self, agreement_id):
        return self.query('SELECT * FROM money_order WHERE agreement_id = ? ORDER BY id', agreement_id)

    @retry(stop_max_delay=15000)
    def wait_tax_report_status(self, report_id, status):
        """Ждёт, пока заявка на справку перейдёт в нужный статус."""
        report = self.query('SELECT * FROM tax_report WHERE id = ?', report_id, fetch_one=True)
        assert report['status'] == status, f"Справка {report_id}: статус {report['status']}, ожидался {status}"
        return report
