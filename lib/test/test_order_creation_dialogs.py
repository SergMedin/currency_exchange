import unittest
import os

from ..application import Application
from ..tg import TelegramMock
from ..db_sqla import SqlDb


class TestOrderCreationDialogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if os.path.exists("./tg_data/app_db.json"):
            os.remove("./tg_data/app_db.json")

    def setUp(self):
        self.tg = TelegramMock()
        self.db = SqlDb()
        self.app = Application(self.db, self.tg, debug_mode=True)

    def tearDown(self) -> None:
        self.app._app_db.close()

    def test_start_command(self):
        self.tg.emulate_incoming_message(1, "Joe", "/start")
        self.assertEqual(1, len(self.tg.outgoing))
        m = self.tg.outgoing[0]
        self.assertEqual("Joe", m.user_name)
        self.assertIn("create_order", m.inline_keyboard[0][0].callback_data)
        self.assertEqual("Markdown", m.parse_mode)
