import unittest
import os

from ..application import Application
from ..botlib.tg import TelegramMock
from ..currency_rates import CurrencyMockClient
from ..db_sqla import SqlDb


class TestOrderCreationDialogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if os.path.exists("./tg_data/app_db.json"):
            os.remove("./tg_data/app_db.json")

    def setUp(self):
        self.tg = TelegramMock()
        self.db = SqlDb()
        self.app = Application(self.db, self.tg, currency_client=CurrencyMockClient())
