import unittest
from ..tg_app import TgApp
from ..tg import TelegramMock
from ..db import SQLiteDb


class T(unittest.TestCase):
    def testSimpleMatch(self):
        tg = TelegramMock()
        db = SQLiteDb()
        _ = TgApp(db, tg)
        tg.add_message(1, "SELL 1500 usd * 98.1 rub")
        tg.add_message(2, "BUY 1500 usd * 98.1 rub")
        # print(tg.outgoing)
        self.assertEqual(2, len(tg.outgoing))

    def testSimpleNoMatch(self):
        tg = TelegramMock()
        db = SQLiteDb()
        _ = TgApp(db, tg)
        tg.add_message(1, "SELL 1500 usd * 98.1 rub")
        tg.add_message(2, "BUY 1500 usd * 98.01 rub")
        # print(tg.outgoing)
        self.assertEqual(0, len(tg.outgoing))

    def testSimpleBestPrice(self):
        tg = TelegramMock()
        db = SQLiteDb()
        _ = TgApp(db, tg)
        tg.add_message(1, "SELL 1500 usd * 98.1 rub")
        tg.add_message(2, "SELL 1500 usd * 100 rub")
        tg.add_message(3, "SELL 1500 usd * 110 rub")
        tg.add_message(100, "BUY 1500 usd * 98.1 rub")
        # print(tg.outgoing)
        self.assertEqual(2, len(tg.outgoing))
        self.assertTrue("for 98.10 per unit" in tg.outgoing[0].text)
