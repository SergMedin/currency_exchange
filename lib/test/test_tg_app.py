import unittest
from ..tg_app import TgApp
from ..tg import TelegramMock
from ..db_sqla import SqlDb


class TestTgApp(unittest.TestCase):
    def setUp(self):
        self.tg = TelegramMock()
        self.db = SqlDb()
        self.app = TgApp(self.db, self.tg)

    def test_simple_match(self):
        self.tg.emulate_incoming_message(1, "SELL 1500 RUB * 98.1 AMD min_amt 100")
        self.tg.emulate_incoming_message(2, "BUY 1500 RUB * 98.1 AMD min_amt 100")
        self.assertEqual(2, len(self.tg.outgoing))

    def test_simple_no_match(self):
        self.tg.emulate_incoming_message(1, "SELL 1500 RUB * 98.1 AMD min_amt 100")
        self.tg.emulate_incoming_message(2, "BUY 1500 RUB * 98.01 AMD min_amt 100")
        self.assertEqual(0, len(self.tg.outgoing))

    def test_simple_best_price(self):
        self.tg.emulate_incoming_message(1, "SELL 1500 RUB * 98.1 AMD min_amt 100")
        self.tg.emulate_incoming_message(2, "SELL 1500 RUB * 100 AMD min_amt 100")
        self.tg.emulate_incoming_message(3, "SELL 1500 RUB * 110 AMD min_amt 100")
        self.tg.emulate_incoming_message(100, "BUY 1500 RUB * 98.1 AMD min_amt 100")
        self.assertEqual(2, len(self.tg.outgoing))
        self.assertIn("for 98.10 per unit", self.tg.outgoing[0].text)

    def test_check_price_valid(self):
        self.tg.emulate_incoming_message(1, "SELL 1000 RUB * 4.54 AMD min_amt 100")

    def test_check_price_invalid_decimal(self):
        self.tg.emulate_incoming_message(1, "SELL 1000 RUB * 4.541 AMD min_amt 100")
        self.assertIn("Price has more than two digits after the decimal point", self.tg.outgoing[0].text)

    def test_check_price_invalid_value(self):
        self.tg.emulate_incoming_message(1, "SELL 1000 RUB * INVALID AMD min_amt 100")
        self.assertIn("Invalid value for Decimal", self.tg.outgoing[0].text)

    def test_check_min_op_threshold_negative_value(self):
        self.tg.emulate_incoming_message(1, "SELL 1000 RUB * INVALID AMD min_amt -100")
        self.assertIn("Minimum operational threshold cannot be negative", self.tg.outgoing[0].text)
