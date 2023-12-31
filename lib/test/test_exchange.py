import unittest
from .. import exchange
from ..db import DbMock
from ..data import Order, User, OrderType

from ..logger import get_logger
logger = get_logger(__name__)


class T(unittest.TestCase):

    def testConstruction(self):
        db = DbMock()
        exchange.Exchange(db, None)

    def testSimpleDealWithEqualAmounts(self):
        db = DbMock()
        matches = []
        e = exchange.Exchange(db, lambda m: matches.append(m))
        e.new_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0))
        e.new_order(Order(User(2), OrderType.BUY, 98.0, 1299.0, 500.0))
        self.assertEqual(len(matches), 1)

    # def testSimpleNoMatch(self):
    #     db = DbMock()
    #     matches = []
    #     e = exchange.Exchange(db, lambda m: matches.append(m))
    #     e.on_new_order(Order(User(1), OrderType.SELL, 98.01, 1299.0, 500.0))
    #     e.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1299.0, 500.0))
    #     self.assertEqual(len(matches), 0)

    def testDifferentPricesSellMoreThanBuy(self):
        db = DbMock()
        matches = []
        e = exchange.Exchange(db, lambda m: matches.append(m))
        e.new_order(Order(User(1), OrderType.SELL, 100.0, 1299.0, 500.0))
        e.new_order(Order(User(2), OrderType.BUY, 98.0, 1299.0, 500.0))
        self.assertEqual(len(matches), 0)

    def testDifferentPricesSellLessThanBuy(self):
        logger.debug("testDifferentPricesSellLessThanBuy")
        db = DbMock()
        matches = []
        e = exchange.Exchange(db, lambda m: matches.append(m))
        e.new_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0))
        e.new_order(Order(User(2), OrderType.BUY, 100.0, 1299.0, 500.0))
        self.assertEqual(len(matches), 1)

    def testManyOrders(self):
        logger.debug("TEST MANY ORDERS")
        db = DbMock()
        matches = []
        e = exchange.Exchange(db, lambda m: matches.append(m))
        e.new_order(Order(User(1), OrderType.SELL, 100.0, 1299.0, 500.0))
        e.new_order(Order(User(2), OrderType.BUY, 98.0, 1500.0, 500.0))
        e.new_order(Order(User(3), OrderType.SELL, 102.0, 2000.0, 500.0))
        e.new_order(Order(User(1), OrderType.BUY, 110.0, 3000.0, 500.0))
        self.assertEqual(len(matches), 2)
