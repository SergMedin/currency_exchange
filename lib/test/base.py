import unittest
from lib.application import Application

from lib.botlib.tg import TelegramMock
from lib.currency_rates import CurrencyMockClient
from lib.db_sqla import SqlDb
from lib.rep_sys.rep_id import RepSysUserId
from lib.rep_sys.rep_sys import ReputationSystem


class ExchgTestBase(unittest.TestCase):
    def setUp(self):
        self.admin_contacts = [3, 4, 5]
        self.tg = TelegramMock()
        self.db = SqlDb()
        self.rep_sys = ReputationSystem(self.db.engine)
        self.app = Application(
            self.db,
            self.tg,
            currency_client=CurrencyMockClient(),
            rep_sys=self.rep_sys,
            admin_contacts=self.admin_contacts,
        )
        self.rep_sys.set_authenticity(RepSysUserId(1), True)
