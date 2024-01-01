import unittest
from ..tg_app import TgApp
from ..tg import TelegramMock
from ..db import SQLiteDb


class TestTgApp(unittest.TestCase):
    def setUp(self):
        self.tg = TelegramMock()
        self.db = SQLiteDb()
        self.app = TgApp(self.db, self.tg)

    def test_simple_match(self):
        self.tg.add_message(1, "SELL 1500 usd * 98.1 rub")
        self.tg.add_message(2, "BUY 1500 usd * 98.1 rub")
        self.assertEqual(2, len(self.tg.outgoing))

    def test_simple_no_match(self):
        self.tg.add_message(1, "SELL 1500 usd * 98.1 rub")
        self.tg.add_message(2, "BUY 1500 usd * 98.01 rub")
        self.assertEqual(0, len(self.tg.outgoing))

    def test_simple_best_price(self):
        self.tg.add_message(1, "SELL 1500 usd * 98.1 rub")
        self.tg.add_message(2, "SELL 1500 usd * 100 rub")
        self.tg.add_message(3, "SELL 1500 usd * 110 rub")
        self.tg.add_message(100, "BUY 1500 usd * 98.1 rub")
        self.assertEqual(2, len(self.tg.outgoing))
        self.assertIn("for 98.10 per unit", self.tg.outgoing[0].text)
