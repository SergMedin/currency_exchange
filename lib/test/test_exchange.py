import unittest
from .. import exchange
from ..db import DbMock
from ..data import Order, User, OrderType


class T(unittest.TestCase):

    def testConstruction(self):
        db = DbMock()
        exchange.Exchange(db, None)

    def testSimpleDealWithEqualAmounts(self):
        db = DbMock()
        matches = []
        e = exchange.Exchange(db, lambda m: matches.append(m))
        e.on_new_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0))
        e.on_new_order(Order(User(1), OrderType.BUY, 98.0, 1299.0, 500.0))
        self.assertEqual(len(matches), 1)

    def testSimpleNoMatch(self):
        db = DbMock()
        matches = []
        e = exchange.Exchange(db, lambda m: matches.append(m))
        e.on_new_order(Order(User(1), OrderType.SELL, 98.01, 1299.0, 500.0))
        e.on_new_order(Order(User(1), OrderType.BUY, 98.0, 1299.0, 500.0))
        self.assertEqual(len(matches), 0)
