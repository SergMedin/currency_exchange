import time
import unittest
import threading
from ..exchange import Exchange
from ..db_sqla import SqlDb
from ..data import Order, User, OrderType
from ..gsheets_loger import GSheetsLoger
from decimal import Decimal

from ..logger import get_logger
logger = get_logger(__name__)


class T(unittest.TestCase):
    lock = threading.RLock()
    no = 0

    def setUp(self):
        self.db = SqlDb()
        self.matches = []
        with T.lock:
            seq_no = T.no
            T.no += 1
        endp = f"inproc://orders.log.{seq_no}"
        self.exchange = Exchange(self.db, lambda m: self.matches.append(m), zmq_orders_log_endpoint=endp)
        self.loger = GSheetsLoger(zmq_endpoint=endp)
        self.loger.start()

    def tearDown(self) -> None:
        self.exchange.dtor()
        self.loger.stop()
        return super().tearDown()

    def testConstruction(self):
        logger.debug('[ testConstruction ]'.center(80, '|'))
        Exchange(self.db, None)

    def testSimpleDealWithEqualAmounts(self):
        logger.debug('[ testSimpleDealWithEqualAmounts ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testPersistance(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.exchange = Exchange(self.db, lambda m: self.matches.append(m))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testDifferentPricesSellMoreThanBuy(self):
        logger.debug('[ testDifferentPricesSellMoreThanBuy ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 10.0, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 9.8, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.assertEqual(len(self.matches), 0)

    def testDifferentPricesSellLessThanBuy(self):
        logger.debug('[ testDifferentPricesSellLessThanBuy ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 9.81, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 10.0, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testManyOrders(self):
        logger.debug('[ testManyOrders ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 100.0, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1500.0, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(3), OrderType.BUY, 102.0, 1500.0, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 120.0, 2000.0, 500.0, lifetime_sec=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testMinOpThresholdSuitable(self):
        logger.debug('[ testDifferentPricesSellLessThanBuy ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 4.51, 1000, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 4.55, 2000, 1000.0, lifetime_sec=48*60*60))
        self.assertEqual(len(self.matches), 1)

    def testMinOpThresholdUnsuitable(self):
        logger.debug('[ testDifferentPricesSellLessThanBuy ]'.center(80, '|'))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 4.51, 1000, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 4.55, 2000, 2000.0, lifetime_sec=48*60*60))
        self.assertEqual(len(self.matches), 0)

    def testOrderLifetimeExceeded(self):
        logger.debug('[ testOrderLifetimeExceeded ]'.center(80, '|'))
        self.exchange.on_new_order(Order(user=User(1), type=OrderType.BUY, price=100.0, amount_initial=100.0,
                                   min_op_threshold=50.0, lifetime_sec=60*60, creation_time=time.time() - 2 * 3600))
        self.exchange.on_new_order(Order(user=User(2), type=OrderType.BUY, price=100.0, amount_initial=100.0,
                                   min_op_threshold=50.0, lifetime_sec=60*60, creation_time=time.time() - 0.5 * 3600))
        self.exchange.on_new_order(Order(user=User(3), type=OrderType.BUY, price=100.0,
                                   amount_initial=100.0, min_op_threshold=50.0, lifetime_sec=60*60))
        # The first order should be removed after adding the second one:
        self.assertEqual(len(self.exchange._orders), 2)

    def testOrderLifetimeIncorrectInput(self):
        logger.debug('[ testOrderLifetimeIncorrectInput ]'.center(80, '|'))
        with self.assertRaises(ValueError):
            self.exchange.on_new_order(Order(user=User(1), type=OrderType.BUY, price=100.0,
                                       amount_initial=100.0, min_op_threshold=50.0, lifetime_sec=50*60*60))

    def testGetStatsNoOrders(self):
        expected_result = {
            'data': {
                'order_cnt': 0,
                'user_cnt': 0,
                'max_buyer_price': None,
                'max_buyer_min_op_threshold': None,
                'min_seller_price': None,
                'min_seller_min_op_threshold': None,
            },
            'text': "No buyers :(\n\nNo sellers :("
        }
        result = self.exchange.get_stats()
        self.assertEqual(result, expected_result)

    def testGetStatsWithOrders(self):
        self.exchange.on_new_order(Order(User(1, 'Joe'), OrderType.SELL, 4.90, 1000, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(2, 'Doe'), OrderType.BUY, 4.55, 2000, 1000.0, lifetime_sec=48*60*60))

        expected_result = {
            'data': {
                'order_cnt': 2,
                'user_cnt': 2,
                'max_buyer_price': Decimal('4.55'),
                'max_buyer_min_op_threshold': Decimal('1000'),
                'min_seller_price': Decimal('4.9'),
                'min_seller_min_op_threshold': Decimal('500'),
            },
            'text': (
                "best buyer:\n  * price: 4.55 AMD/RUB\n"
                "  * min_op_threshold: 1000 RUB\n\n"
                "best seller:\n  * price: 4.9 AMD/RUB\n"
                "  * min_op_threshold: 500 RUB"
            )
        }
        result = self.exchange.get_stats()
        self.assertEqual(result, expected_result)

    def test_loger_simple(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1299.0, 500.0, lifetime_sec=48*60*60))
        self.assertEqual(len(self.matches), 1)
        time.sleep(0.1)
        t = self.loger._gst
        self.assertEqual(t.cell(GSheetsLoger.iii-1, 2), "new_order")
