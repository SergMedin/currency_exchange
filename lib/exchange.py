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
        if o.lifetime_sec > ORDER_LIFETIME_LIMIT:
            raise ValueError("Order lifetime cannot exceed 48 hours")

        o = self._db.store_order(o)
        self._orders[o._id] = o
        self._check_order_lifetime()  # Removing expired orders
        self._process_matches()

    def list_orders_for_user(self, user: data.User) -> list[data.Order]:
        return [o for o in self._orders.values() if o.user == user]

    def _check_order_lifetime(self) -> None:
        """
        Check the lifetime of orders and remove expired orders.

        This method iterates through all the orders in the exchange and checks if their lifetime has exceeded.
        If an order's lifetime has exceeded, it is removed from the exchange.

        Returns:
            None
        """
        current_time = time.time()
        expired_orders = [
            o
            for o in self._orders.values()
            if (current_time - o.creation_time) > o.lifetime_sec
        ]
        for o in expired_orders:
            self.remove_order(o._id)

    def _process_matches(self) -> None:
        logger.debug("=[ _process_matches: new iteration ]=".center(80, "-"))
        sellers = sorted(
            [o for o in self._orders.values() if o.type == data.OrderType.SELL],
            key=lambda x: x.creation_time,
        )
        buyers = sorted(
            [o for o in self._orders.values() if o.type == data.OrderType.BUY],
            key=lambda x: x.creation_time,
        )

        logger.debug(f"S: {sellers}\nB: {buyers}\n")

        for seller in sellers:
            for buyer in buyers:
                if (
                    buyer.price >= seller.price
                    and seller.amount_left >= buyer.min_op_threshold
                    and buyer.amount_left >= seller.min_op_threshold
                ):
                    match_amount = min(buyer.amount_left, seller.amount_left)
                    mid_price = round((seller.price + buyer.price) / 2, 2)

                    match = data.Match(
                        dataclasses.replace(seller),
                        dataclasses.replace(buyer),
                        mid_price,
                        match_amount,
                    )
                    logger.debug(f"match: {match}")
                    if self._on_match:
                        self._on_match(match)

                    seller.amount_left -= match_amount
                    buyer.amount_left -= match_amount

                    # Remove order if amount_left is less than or equal to 0
                    if seller.amount_left <= 0:
                        self.remove_order(seller._id)
                    else:
                        seller.min_op_threshold = min(seller.amount_left, seller.min_op_threshold)

                    if buyer.amount_left <= 0:
                        self.remove_order(buyer._id)
                    else:
                        buyer.min_op_threshold = min(buyer.amount_left, buyer.min_op_threshold)

                    # Breaking out of the loop if the current order is fully matched
                    if seller.amount_left <= 0 or buyer.amount_left <= 0:
                        break

            # If the seller's order is fully matched, move on to the next seller
            if seller.amount_left <= 0:
                continue

    def remove_order(self, _id: int) -> None:
        del self._orders[_id]
        self._db.remove_order(_id)

    def get_stats(self) -> dict:
        sellers = [o for o in self._orders.values() if o.type == data.OrderType.SELL]
        buyers = [o for o in self._orders.values() if o.type == data.OrderType.BUY]

        if sellers:
            sellers.sort(key=lambda x: x.price)
            best_seller = sellers[0]
            min_seller_price = best_seller.price
            min_seller_min_op_threshold = best_seller.min_op_threshold
            min_seller_text = (
                f"best seller:\n  * price: {min_seller_price} AMD/RUB\n"
                f"  * min_op_threshold: {min_seller_min_op_threshold} RUB"
            )
        else:
            min_seller_text = "No sellers :("
            min_seller_price = None
            min_seller_min_op_threshold = None
        if buyers:
            buyers.sort(key=lambda x: -x.price)
            best_buyer = buyers[0]
            max_buyer_price = best_buyer.price
            max_buyer_min_op_threshold = best_buyer.min_op_threshold
            max_buyer_text = (
                f"best buyer:\n  * price: {max_buyer_price} AMD/RUB\n"
                f"  * min_op_threshold: {max_buyer_min_op_threshold} RUB"
            )
        else:
            max_buyer_text = "No buyers :("
            max_buyer_price = None
            max_buyer_min_op_threshold = None

        return {
            'data': {
                'order_cnt': len(self._orders),
                'user_cnt': len(set([o.user.id for o in self._orders.values()])),
                'max_buyer_price': max_buyer_price,
                'max_buyer_min_op_threshold': max_buyer_min_op_threshold,
                'min_seller_price': min_seller_price,
                'min_seller_min_op_threshold': min_seller_min_op_threshold,
            },
            'text': (
                f"{max_buyer_text}\n\n"
                f"{min_seller_text}"
            ),
        }


class T(unittest.TestCase):
    pass
