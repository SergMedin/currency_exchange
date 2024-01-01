import time
import unittest
from ..exchange import Exchange
from ..db_sqla import SqlDb
from ..data import Order, User, OrderType

from ..logger import get_logger
logger = get_logger(__name__)


class T(unittest.TestCase):

    def setUp(self):
        self.db = SqlDb()
        self.matches = []
        self.exchange = Exchange(self.db, lambda m: self.matches.append(m))

    def testConstruction(self):
        logger.debug('[ testConstruction ]'.center(80, '|'))
        Exchange(self.db, None)

    def testSimpleDealWithEqualAmounts(self):
        logger.debug('[ testSimpleDealWithEqualAmounts ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1299.0, 500.0, lifetime=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testPersistance(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48*60*60))
        self.exchange = Exchange(self.db, lambda m: self.matches.append(m))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1299.0, 500.0, lifetime=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testDifferentPricesSellMoreThanBuy(self):
        logger.debug('[ testDifferentPricesSellMoreThanBuy ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 10.0, 1299.0, 500.0, lifetime=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 9.8, 1299.0, 500.0, lifetime=48*60*60))
        self.assertEqual(len(self.matches), 0)

    def testDifferentPricesSellLessThanBuy(self):
        logger.debug('[ testDifferentPricesSellLessThanBuy ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 9.81, 1299.0, 500.0, lifetime=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 10.0, 1299.0, 500.0, lifetime=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testManyOrders(self):
        logger.debug('[ testManyOrders ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 100.0, 1299.0, 500.0, lifetime=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1500.0, 500.0, lifetime=48*60*60))
        self.exchange.on_new_order(Order(User(3), OrderType.BUY, 102.0, 1500.0, 500.0, lifetime=48*60*60))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 120.0, 2000.0, 500.0, lifetime=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testMinOpThresholdSuitable(self):
        logger.debug('[ testDifferentPricesSellLessThanBuy ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 4.51, 1000, 500.0, lifetime=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 4.55, 2000, 1000.0, lifetime=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testMinOpThresholdUnsuitable(self):
        logger.debug('[ testDifferentPricesSellLessThanBuy ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 4.51, 1000, 500.0, lifetime=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 4.55, 2000, 2000.0, lifetime=48*60*60))
        self.assertEqual(len(self.matches), 0)

    def testOrderLifetimeExceeded(self):
        logger.debug('[ testOrderLifetimeExceeded ]'.center(80, '|'))
        self.exchange.on_new_order(Order(user=User(1), type=OrderType.BUY, price=100.0, amount_initial=100.0,
                                   min_op_threshold=50.0, lifetime=60*60, creation_time=time.time() - 2 * 3600))
        self.exchange.on_new_order(Order(user=User(2), type=OrderType.BUY, price=100.0, amount_initial=100.0,
                                   min_op_threshold=50.0, lifetime=60*60, creation_time=time.time() - 0.5 * 3600))
        self.exchange.on_new_order(Order(user=User(3), type=OrderType.BUY, price=100.0,
                                   amount_initial=100.0, min_op_threshold=50.0, lifetime=60*60))
        # The first order should be removed after adding the second one:
        self.assertEqual(len(self.exchange._orders), 2)

    def testOrderLifetimeIncorrectInput(self):
        logger.debug('[ testOrderLifetimeIncorrectInput ]'.center(80, '|'))
        with self.assertRaises(ValueError):
            self.exchange.on_new_order(Order(user=User(1), type=OrderType.BUY, price=100.0,
                                       amount_initial=100.0, min_op_threshold=50.0, lifetime=50*60*60))
