from .config import ORDER_LIFETIME_LIMIT
import time
import dataclasses
import unittest
from .db import Db
from . import data

from .logger import get_logger
logger = get_logger(__name__)


class Exchange:
    # FIXME: isn't it better not to store any orders in memory and go through the db on every event instead?

    def __init__(self, db: Db, on_match=None):
        self._db = db
        self._on_match = on_match
        orders = []
        self._db.iterate_orders(lambda o: orders.append((o._id, o)))
        self._orders: dict[int, data.Order] = dict(orders)

    def on_new_order(self, o: data.Order) -> None:
        if o.lifetime > ORDER_LIFETIME_LIMIT:
            raise ValueError("Order lifetime cannot exceed 48 hours")

        o = self._db.store_order(o)
        self._orders[o._id] = o
        self._check_order_lifetime()  # Removing expired orders
        self._process_matches()

    def _check_order_lifetime(self) -> None:
        """
        Check the lifetime of orders and remove expired orders.

        This method iterates through all the orders in the exchange and checks if their lifetime has exceeded.
        If an order's lifetime has exceeded, it is removed from the exchange.

        Returns:
            None
        """
        current_time = time.time()
        expired_orders = [o for o in self._orders.values() if (current_time - o.creation_time) > o.lifetime]
        for o in expired_orders:
            self._remove_order(o._id)

    def _process_matches(self) -> None:
        while True:
            logger.debug('=[ _process_matches: new interation ]='.center(80, '-'))
            sellers, buyers = [[o for o in self._orders.values() if o.type == t]
                               for t in [data.OrderType.SELL, data.OrderType.BUY]]

            logger.debug(f'S: {sellers}\nB: {buyers}\n')

            if len(sellers) <= 0 or len(buyers) <= 0:
                break

            sellers.sort(key=lambda x: x.price)
            buyers.sort(key=lambda x: -x.price)

            so = sellers[0]
            bo = buyers[0]

            logger.debug(f'so: {so}\nbo: {bo}\n')

            # FIXME:
            #   - it now ignores min_thershold
            #   - It doesn't check the uniqueness of user_id (bug or feature?)
            if bo.price >= so.price:
                amount = min(bo.amount_left, so.amount_left)
                match = data.Match(dataclasses.replace(so), dataclasses.replace(bo),
                                   round((so.price+bo.price)/2, 2), amount)
                logger.debug(f'match: {match}')
                if self._on_match:
                    self._on_match(match)
                so.amount_left -= amount
                bo.amount_left -= amount
                for o in (so, bo):
                    if o.amount_left <= 0:
                        self._remove_order(o._id)
            else:
                break

    def _remove_order(self, _id: int) -> None:
        del self._orders[_id]
        self._db.remove_order(_id)


class T(unittest.TestCase):
    pass
