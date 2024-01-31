import unittest
from ..app import ShoesShopApp, GoogleSheetsConfig
from lib.tg import TelegramMock
from lib.gspreads import GSpreadsTableMock

# from ..db_sqla import SqlDb


class TestBootShopApp(unittest.TestCase):
    def setUp(self):
        self.tg = TelegramMock()
        self.gs = GSpreadsTableMock()

    def _init_table(self):
        table = [
            ["Всего", "Размеры"],
            ["", ""],
            [0, "34"],
            [5, "35"],
            [6, "36"],
            [4, "37"],
            [7, "38"],
            [6, "39"],
            [0, "40"],
            [0, "41"],
            [0, "42"],
            [0, "43"],
            [0, "44"],
            [1, "45"],
            [0, "46"],
            [0, "спец"],
        ]
        for rowi, rowv in enumerate(table):
            for coli, v in enumerate(rowv):
                self.gs.update_cell(rowi + 1, coli + 1, v)

    def test_simple(self):
        self._init_table()
        app = ShoesShopApp(self.tg, GoogleSheetsConfig(mock=self.gs))
        self.assertEqual(len(app._stocks.sizes), 14)
