import time
import unittest
import threading
from ..exchange import Exchange
from ..db_sqla import SqlDb
from ..data import Order, User, OrderType
from ..gsheets_loger import GSheetsLoger
from ..config import ORDER_LIFETIME_LIMIT
from decimal import Decimal
import os

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
        gsk = os.getenv("GOOGLE_SPREADSHEET_KEY", None)
        gsst = os.getenv("GOOGLE_SPREADSHEET_SHEET_TITLE", None)
        self.loger = GSheetsLoger(endp, gsk, gsst)
        self.loger.start()

    def tearDown(self) -> None:
        self.exchange.dtor()
        self.loger.stop()
        return super().tearDown()

    def testConstruction(self):
        logger.debug("[ testConstruction ]".center(80, "|"))
        Exchange(self.db, None)

    def testProcessMatchesSingleMatch(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 1)
        self.assertEqual(self.matches[0].sell_order.amount_left, 0)
        self.assertEqual(self.matches[0].buy_order.amount_left, 0)

    def testProcessMatchesMultipleMatches(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.SELL, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.exchange._orders), 2)
        self.exchange.on_new_order(Order(User(3), OrderType.BUY, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 2)
        self.assertEqual(len(self.exchange._orders), 0)
        self.assertEqual(self.matches[0].sell_order.amount_left, 0)
        self.assertEqual(self.matches[0].buy_order.amount_left, 50)
        self.assertEqual(self.matches[1].sell_order.amount_left, 0)
        self.assertEqual(self.matches[1].buy_order.amount_left, 0)

    def testProcessMatchesMultipleMatches2(self):
        self.exchange.on_new_order(Order(User(1), OrderType.BUY, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.exchange._orders), 2)
        self.exchange.on_new_order(Order(User(3), OrderType.SELL, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 2)
        self.assertEqual(len(self.exchange._orders), 0)
        self.assertEqual(self.matches[0].sell_order.amount_left, 50)
        self.assertEqual(self.matches[0].buy_order.amount_left, 0)
        self.assertEqual(self.matches[1].sell_order.amount_left, 0)
        self.assertEqual(self.matches[1].buy_order.amount_left, 0)

    def testProcessMatchesPartialMatch(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 10.0, 150.0, 25.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 1)
        self.assertEqual(self.matches[-1].sell_order.amount_left, 0)
        self.assertEqual(self.matches[-1].buy_order.amount_left, 100.0)
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 10.0, 200.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 2)
        self.assertEqual(self.matches[-1].sell_order.amount_left, 100.0)
        self.assertEqual(self.matches[-1].buy_order.amount_left, 0)

    def testProcessMatchesOrderRemoval(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.exchange._orders), 0)

    def testProcessMatchesMinOpThresholdUpdate(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 10.0, 120.0, 75.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(self.exchange._orders[2].min_op_threshold, 20.0)

    def testDifferentPricesSellMoreThanBuy(self):
        logger.debug("[ testDifferentPricesSellMoreThanBuy ]".center(80, "|"))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 10.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 9.8, 1299.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 0)

    def testDifferentPricesSellLessThanBuy(self):
        logger.debug("[ testDifferentPricesSellLessThanBuy ]".center(80, "|"))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 9.81, 1299.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 10.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 1)

    def testManyOrders(self):
        logger.debug("[ testManyOrders ]".center(80, "|"))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 100.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1500.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(3), OrderType.BUY, 102.0, 1500.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 120.0, 2000.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 1)

    def testMinOpThresholdSuitable(self):
        logger.debug("[ testDifferentPricesSellLessThanBuy ]".center(80, "|"))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 4.51, 1000, 500.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 4.55, 2000, 1000.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 1)

    def testMinOpThresholdUnsuitable(self):
        logger.debug("[ testDifferentPricesSellLessThanBuy ]".center(80, "|"))
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 4.51, 1000, 500.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 4.55, 2000, 2000.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 0)

    def testOrderLifetimeExceeded(self):
        logger.debug("[ testOrderLifetimeExceeded ]".center(80, "|"))
        self.exchange.on_new_order(
            Order(
                user=User(1),
                type=OrderType.BUY,
                price=100.0,
                amount_initial=100.0,
                min_op_threshold=50.0,
                lifetime_sec=60 * 60,
                creation_time=time.time() - 2 * 3600,
            )
        )
        self.exchange.on_new_order(
            Order(
                user=User(2),
                type=OrderType.BUY,
                price=100.0,
                amount_initial=100.0,
                min_op_threshold=50.0,
                lifetime_sec=60 * 60,
                creation_time=time.time() - 0.5 * 3600,
            )
        )
        self.exchange.on_new_order(
            Order(
                user=User(3),
                type=OrderType.BUY,
                price=100.0,
                amount_initial=100.0,
                min_op_threshold=50.0,
                lifetime_sec=60 * 60,
            )
        )
        # The first order should be removed after adding the second one:
        self.assertEqual(len(self.exchange._orders), 2)

    def testOrderLifetimeIncorrectInput(self):
        logger.debug("[ testOrderLifetimeIncorrectInput ]".center(80, "|"))
        with self.assertRaises(ValueError):
            self.exchange.on_new_order(
                Order(
                    user=User(1),
                    type=OrderType.BUY,
                    price=100.0,
                    amount_initial=100.0,
                    min_op_threshold=50.0,
                    lifetime_sec=ORDER_LIFETIME_LIMIT + 1,
                )
            )

    def testGetStatsNoOrders(self):
        expected_result = {
            "last_match_price": None,
            "order_cnt": 0,
            "user_cnt": 0,
            "max_buyer_price": None,
            "max_buyer_min_op_threshold": None,
            "min_seller_price": None,
            "min_seller_min_op_threshold": None,
            "total_amount_buyers": Decimal("0"),
            "total_amount_sellers": Decimal("0"),
        }
        result = self.exchange.get_stats()["data"]
        self.assertIn("currency_rate", result.keys())
        del result["currency_rate"]
        self.assertEqual(result, expected_result)

    def testGetStatsWithOrders(self):
        self.exchange.on_new_order(
            Order(
                User(1, "Joe"),
                OrderType.SELL,
                4.90,
                1000,
                500.0,
                lifetime_sec=48 * 60 * 60,
            )
        )
        self.exchange.on_new_order(
            Order(
                User(2, "Doe"),
                OrderType.BUY,
                4.55,
                2000,
                1000.0,
                lifetime_sec=48 * 60 * 60,
            )
        )
        self.exchange.on_new_order(
            Order(
                User(2, "Doe"),
                OrderType.BUY,
                4.55,
                3000,
                1000.0,
                lifetime_sec=48 * 60 * 60,
            )
        )

        expected_result = {
            "last_match_price": None,
            "order_cnt": 3,
            "user_cnt": 2,
            "max_buyer_price": Decimal("4.55"),
            "max_buyer_min_op_threshold": Decimal("1000"),
            "min_seller_price": Decimal("4.9"),
            "min_seller_min_op_threshold": Decimal("500"),
            "total_amount_buyers": Decimal("5000"),
            "total_amount_sellers": Decimal("1000"),
        }
        result = self.exchange.get_stats()["data"]
        self.assertIn("currency_rate", result.keys())
        del result["currency_rate"]
        self.assertEqual(result, expected_result)

    def test_loger_simple(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 1)
        time.sleep(0.1)
        t = self.loger._gst
        self.assertEqual(t.cell(self.loger._curr_row - 1, 2), "new_order")


class ExchangeTestsWithDatabaseFile(unittest.TestCase):
    lock = threading.RLock()
    no = 0

    def setUp(self):
        if os.path.exists("unittest_database.sqlite"):
            os.remove("unittest_database.sqlite")
        self.db = SqlDb(conn_str="sqlite:///unittest_database.sqlite")
        self.matches = []
        with T.lock:
            seq_no = T.no
            T.no += 1
        endp = f"inproc://orders.log.{seq_no}"
        self.exchange = Exchange(self.db, lambda m: self.matches.append(m), zmq_orders_log_endpoint=endp)
        gsk = os.getenv("GOOGLE_SPREADSHEET_KEY", None)
        gsst = os.getenv("GOOGLE_SPREADSHEET_SHEET_TITLE", None)
        self.loger = GSheetsLoger(endp, gsk, gsst)
        self.loger.start()

    def tearDown(self):
        self.exchange.dtor()
        self.loger.stop()
        self.db._eng.dispose()
        if os.path.exists("unittest_database.sqlite"):
            os.remove("unittest_database.sqlite")
        return super().tearDown()

    def testPersistance(self):
        self.exchange.on_new_order(Order(User(1), OrderType.SELL, 98.0, 1400.0, 100.0, lifetime_sec=48 * 60 * 60))
        self.exchange.on_new_order(Order(User(2), OrderType.BUY, 98.0, 1000.0, 100.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.exchange._orders), 1)
        self.matches = []
        self.exchange = Exchange(self.db, lambda m: self.matches.append(m))
        self.assertEqual(len(self.exchange._orders), 1)
        self.assertEqual(self.exchange._orders[1].amount_initial, 1400)
        self.assertEqual(self.exchange._orders[1].amount_left, 400)
        self.exchange.on_new_order(Order(User(3), OrderType.BUY, 98.0, 400.0, 100.0, lifetime_sec=48 * 60 * 60))
        self.assertEqual(len(self.matches), 1)
        self.assertEqual(len(self.exchange._orders), 0)
