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
        logger.debug('=[ _process_matches: new iteration ]='.center(80, '-'))
        sellers = [o for o in self._orders.values() if o.type == data.OrderType.SELL]
        buyers = [o for o in self._orders.values() if o.type == data.OrderType.BUY]

        logger.debug(f'S: {sellers}\nB: {buyers}\n')

        sellers.sort(key=lambda x: x.price)
        buyers.sort(key=lambda x: -x.price)

        for buyer in buyers:
            for seller in sellers:
                if (
                    buyer.price >= seller.price
                    and seller.amount_left >= buyer.min_op_threshold
                    and buyer.amount_left >= seller.min_op_threshold
                ):
                    so = seller
                    bo = buyer
                    break
            else:
                continue
            break

        else:
            return

        logger.debug(f'so: {so}\nbo: {bo}\n')

        amount = min(bo.amount_left, so.amount_left)
        match = data.Match(
            dataclasses.replace(so),
            dataclasses.replace(bo),
            round((so.price + bo.price) / 2, 2),
            amount
        )
        logger.debug(f'match: {match}')
        if self._on_match:
            self._on_match(match)
        so.amount_left -= amount
        bo.amount_left -= amount
        for o in (so, bo):
            if o.amount_left <= 0:
                self._remove_order(o._id)
            elif o.amount_left <= o.min_op_threshold:
                o.min_op_threshold = o.amount_left

    def _remove_order(self, _id: int) -> None:
        del self._orders[_id]
        self._db.remove_order(_id)


class T(unittest.TestCase):
    pass
