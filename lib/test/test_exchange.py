import time
import unittest
import threading
import logging
from decimal import Decimal
import os
from ..exchange import Exchange
from ..db_sqla import SqlDb
from ..data import Order, User, OrderType
from ..config import ORDER_LIFETIME_LIMIT
from ..currency_rates import CurrencyConverter, CurrencyMockClient


class T(unittest.TestCase):
    no = 0

    def setUp(self):
        self.db = SqlDb()
        self.matches = []

        currency_client = CurrencyMockClient()
        currency_converter = CurrencyConverter(currency_client)
        self.exchange = Exchange(
            self.db,
            currency_converter,
            lambda m: self.matches.append(m),
        )

    def testConstruction(self):
        logging.debug("[ testConstruction ]".center(80, "|"))
        currency_client = CurrencyMockClient()
        currency_converter = CurrencyConverter(currency_client)
        Exchange(self.db, currency_converter, None)

    def testProcessMatchesSingleMatch(self):
        self.exchange.place_order(
            Order(User(1), OrderType.SELL, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(2), OrderType.BUY, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 1)
        self.assertEqual(self.matches[0].sell_order.amount_left, 0)
        self.assertEqual(self.matches[0].buy_order.amount_left, 0)

    def testProcessMatchesMultipleMatches(self):
        self.exchange.place_order(
            Order(User(1), OrderType.SELL, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(2), OrderType.SELL, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.exchange._orders), 2)
        self.exchange.place_order(
            Order(User(3), OrderType.BUY, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 2)
        self.assertEqual(len(self.exchange._orders), 0)
        self.assertEqual(self.matches[0].sell_order.amount_left, 0)
        self.assertEqual(self.matches[0].buy_order.amount_left, 50)
        self.assertEqual(self.matches[1].sell_order.amount_left, 0)
        self.assertEqual(self.matches[1].buy_order.amount_left, 0)

    def testProcessMatchesCorrectPriotiry(self):
        self.exchange.place_order(
            Order(User(1), OrderType.SELL, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(2), OrderType.SELL, 8.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(3), OrderType.BUY, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 1)
        self.assertEqual(len(self.exchange._orders), 1)
        self.assertEqual(
            self.exchange._orders[list(self.exchange._orders.keys())[0]].price,
            Decimal(10),
        )

    def testProcessMatchesMultipleMatches2(self):
        self.exchange.place_order(
            Order(User(1), OrderType.BUY, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(2), OrderType.BUY, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.exchange._orders), 2)
        self.exchange.place_order(
            Order(User(3), OrderType.SELL, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 2)
        self.assertEqual(len(self.exchange._orders), 0)
        self.assertEqual(self.matches[0].sell_order.amount_left, 50)
        self.assertEqual(self.matches[0].buy_order.amount_left, 0)
        self.assertEqual(self.matches[1].sell_order.amount_left, 0)
        self.assertEqual(self.matches[1].buy_order.amount_left, 0)

    def testProcessMatchesPartialMatch(self):
        self.exchange.place_order(
            Order(User(1), OrderType.SELL, 10.0, 50.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(2), OrderType.BUY, 10.0, 150.0, 25.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 1)
        self.assertEqual(self.matches[-1].sell_order.amount_left, 0)
        self.assertEqual(self.matches[-1].buy_order.amount_left, 100.0)
        self.exchange.place_order(
            Order(User(1), OrderType.SELL, 10.0, 200.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 2)
        self.assertEqual(self.matches[-1].sell_order.amount_left, 100.0)
        self.assertEqual(self.matches[-1].buy_order.amount_left, 0)

    def testProcessMatchesOrderRemoval(self):
        self.exchange.place_order(
            Order(User(1), OrderType.SELL, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(2), OrderType.BUY, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.exchange._orders), 0)

    def testProcessMatchesMinOpThresholdUpdate(self):
        self.exchange.place_order(
            Order(User(1), OrderType.SELL, 10.0, 100.0, 50.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(2), OrderType.BUY, 10.0, 120.0, 75.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(self.exchange._orders[2].min_op_threshold, 20.0)

    def testDifferentPricesSellMoreThanBuy(self):
        logging.debug("[ testDifferentPricesSellMoreThanBuy ]".center(80, "|"))
        self.exchange.place_order(
            Order(
                User(1), OrderType.SELL, 10.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60
            )
        )
        self.exchange.place_order(
            Order(User(2), OrderType.BUY, 9.8, 1299.0, 500.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 0)

    def testDifferentPricesSellLessThanBuy(self):
        logging.debug("[ testDifferentPricesSellLessThanBuy ]".center(80, "|"))
        self.exchange.place_order(
            Order(
                User(1),
                OrderType.SELL,
                9.8234,
                1299.0,
                500.0,
                lifetime_sec=48 * 60 * 60,
            )
        )
        self.exchange.place_order(
            Order(
                User(2),
                OrderType.BUY,
                10.5678,
                1299.0,
                500.0,
                lifetime_sec=48 * 60 * 60,
            )
        )
        self.assertEqual(len(self.matches), 1)
        self.assertEqual(self.matches[-1].price, Decimal("10.1956"))

    def testManyOrders(self):
        logging.debug("[ testManyOrders ]".center(80, "|"))
        self.exchange.place_order(
            Order(
                User(1), OrderType.SELL, 100.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60
            )
        )
        self.exchange.place_order(
            Order(
                User(2), OrderType.BUY, 98.0, 1500.0, 500.0, lifetime_sec=48 * 60 * 60
            )
        )
        self.exchange.place_order(
            Order(
                User(3), OrderType.BUY, 102.0, 1500.0, 500.0, lifetime_sec=48 * 60 * 60
            )
        )
        self.exchange.place_order(
            Order(
                User(1), OrderType.SELL, 120.0, 2000.0, 500.0, lifetime_sec=48 * 60 * 60
            )
        )
        self.assertEqual(len(self.matches), 1)

    def testMinOpThresholdSuitable(self):
        logging.debug("[ testDifferentPricesSellLessThanBuy ]".center(80, "|"))
        self.exchange.place_order(
            Order(User(1), OrderType.SELL, 4.51, 1000, 500.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(2), OrderType.BUY, 4.55, 2000, 1000.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 1)

    def testMinOpThresholdUnsuitable(self):
        logging.debug("[ testDifferentPricesSellLessThanBuy ]".center(80, "|"))
        self.exchange.place_order(
            Order(User(1), OrderType.SELL, 4.51, 1000, 500.0, lifetime_sec=48 * 60 * 60)
        )
        self.exchange.place_order(
            Order(User(2), OrderType.BUY, 4.55, 2000, 2000.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 0)

    def testOrderLifetimeExceeded(self):
        logging.debug("[ testOrderLifetimeExceeded ]".center(80, "|"))
        self.exchange.place_order(
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
        self.exchange.place_order(
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
        self.exchange.place_order(
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
        logging.debug("[ testOrderLifetimeIncorrectInput ]".center(80, "|"))
        with self.assertRaises(ValueError):
            self.exchange.place_order(
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
        self.exchange.place_order(
            Order(
                User(1, "Joe"),
                OrderType.SELL,
                4.90,
                1000,
                500.0,
                lifetime_sec=48 * 60 * 60,
            )
        )
        self.exchange.place_order(
            Order(
                User(2, "Doe"),
                OrderType.BUY,
                4.55,
                2000,
                1000.0,
                lifetime_sec=48 * 60 * 60,
            )
        )
        self.exchange.place_order(
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


class ExchangeTestsWithDatabaseFile(unittest.TestCase):
    no = 0

    def setUp(self):
        self.db = SqlDb()
        self.matches = []
        currency_client = CurrencyMockClient()
        currency_converter = CurrencyConverter(currency_client)
        self.exchange = Exchange(
            self.db,
            currency_converter,
            lambda m: self.matches.append(m),
        )

    def testPersistance(self):
        self.exchange.place_order(
            Order(
                User(1), OrderType.SELL, 98.0, 1400.0, 100.0, lifetime_sec=48 * 60 * 60
            )
        )
        self.exchange.place_order(
            Order(
                User(2), OrderType.BUY, 98.0, 1000.0, 100.0, lifetime_sec=48 * 60 * 60
            )
        )
        self.assertEqual(len(self.exchange._orders), 1)
        self.matches = []
        currency_client = CurrencyMockClient()
        currency_converter = CurrencyConverter(currency_client)
        self.exchange = Exchange(
            self.db, currency_converter, lambda m: self.matches.append(m)
        )
        self.assertEqual(len(self.exchange._orders), 1)
        self.assertEqual(self.exchange._orders[1].amount_initial, 1400)
        self.assertEqual(self.exchange._orders[1].amount_left, 400)
        self.exchange.place_order(
            Order(User(3), OrderType.BUY, 98.0, 400.0, 100.0, lifetime_sec=48 * 60 * 60)
        )
        self.assertEqual(len(self.matches), 1)
        self.assertEqual(len(self.exchange._orders), 0)
