from typing import List, Tuple
import time
import dataclasses
import unittest
import zmq
import pickle
from decimal import Decimal
from .db import Db
from .config import ORDER_LIFETIME_LIMIT
from . import data

from .logger import get_logger

logger = get_logger(__name__)


class Exchange:
    # FIXME: isn't it better not to store any orders in memory and go through the db on every event instead?

    def __init__(
        self, db: Db, currency_client, on_match=None, zmq_orders_log_endpoint=None
    ):
        self._db = db
        self._on_match = on_match
        orders: List[Tuple[int, data.Order]] = []
        self._log_q = (
            zmq.Context.instance().socket(zmq.PUB) if zmq_orders_log_endpoint else None
        )
        if self._log_q:
            self._log_q.bind(zmq_orders_log_endpoint)

        def add(o: data.Order):
            if o._id is None:
                raise ValueError("Order ID is None")
            orders.append((o._id, o))

        self._db.iterate_orders(add)
        self._orders: dict[int, data.Order] = dict(orders)
        self.last_match_price = self._db.get_last_match_price()

        self.currency_converter = currency_client
        self.currency_rate = self.currency_converter.get_rate("RUB", "AMD")

    def dtor(self):
        if self._log_q:
            self._log_q.close()
            self._log_q = None

    def __del__(self):
        self.dtor()

    def on_new_order(self, o: data.Order) -> None:
        if o.lifetime_sec > ORDER_LIFETIME_LIMIT:
            raise ValueError("Order lifetime cannot exceed 48 hours")

        o = self._db.store_order(o)
        if o._id is None:
            raise ValueError("Order ID is None")
        self._log("new", o)
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
            if o._id is None:
                continue
            self.remove_order(o._id)

    def _update_prices(self) -> None:
        """
        Update the prices of the orders in the exchange.

        This method iterates through all the orders in the exchange and updates their prices.
        The prices are updated according to the current exchange rate.

        Returns:
            None
        """
        self.currency_rate = self.currency_converter.get_rate("RUB", "AMD")
        for order in self._orders.values():
            if (
                order.relative_rate != -1.0
                and order.price != self.currency_rate["rate"] * order.relative_rate
            ):
                order.price = Decimal(
                    self.currency_rate["rate"] * order.relative_rate
                ).quantize(Decimal("0.0001"))
                self._db.update_order(order)

    def _process_matches(self) -> None:
        self._update_prices()

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
                    mid_price = round((seller.price + buyer.price) / 2, 4)
                    seller.amount_left -= match_amount
                    buyer.amount_left -= match_amount
                    self._db.update_order(seller)
                    self._db.update_order(buyer)

                    self.last_match_price = mid_price
                    self._db.store_last_match_price(mid_price)

                    match = data.Match(
                        dataclasses.replace(seller),
                        dataclasses.replace(buyer),
                        mid_price,
                        match_amount,
                    )

                    logger.debug(f"match: {match}")
                    if self._on_match:
                        self._on_match(match)

                    # Remove order if amount_left is less than or equal to 0
                    if seller.amount_left <= 0:
                        assert seller._id is not None
                        self.remove_order(seller._id)
                    else:
                        seller.min_op_threshold = min(
                            seller.amount_left, seller.min_op_threshold
                        )

                    if buyer.amount_left <= 0:
                        assert buyer._id is not None
                        self.remove_order(buyer._id)
                    else:
                        buyer.min_op_threshold = min(
                            buyer.amount_left, buyer.min_op_threshold
                        )

                    # If the seller's amount_left is less than or equal to 0, move on to the next seller
                    if seller.amount_left <= 0:  # or buyer.amount_left <= 0:
                        break

            # If the seller's order is fully matched, move on to the next seller
            # if seller.amount_left <= 0:
            #     continue

    def remove_order(self, _id: int) -> None:
        del self._orders[_id]
        self._db.remove_order(_id)

    def get_stats(self) -> dict:
        self._update_prices()

        sellers = [o for o in self._orders.values() if o.type == data.OrderType.SELL]
        buyers = [o for o in self._orders.values() if o.type == data.OrderType.BUY]

        total_amount_sellers = sum(o.amount_left for o in sellers)
        total_amount_buyers = sum(o.amount_left for o in buyers)

        if sellers:
            sellers.sort(key=lambda x: x.price)
            best_seller = sellers[0]
            min_seller_price = best_seller.price
            min_seller_min_op_threshold = best_seller.min_op_threshold
            min_seller_text = (
                f"best seller:\n"
                f"  * price: {min_seller_price} AMD/RUB\n"
                f"  * min_op_threshold: {min_seller_min_op_threshold} RUB"
            )
        else:
            min_seller_text = "No sellers :("
            min_seller_price = None
            min_seller_min_op_threshold = None
            total_amount_sellers = 0

        if buyers:
            buyers.sort(key=lambda x: -x.price)
            best_buyer = buyers[0]
            max_buyer_price = best_buyer.price
            max_buyer_min_op_threshold = best_buyer.min_op_threshold
            max_buyer_text = (
                f"best buyer:\n"
                f"  * price: {max_buyer_price} AMD/RUB\n"
                f"  * min_op_threshold: {max_buyer_min_op_threshold} RUB"
            )
        else:
            max_buyer_text = "No buyers :("
            max_buyer_price = None
            max_buyer_min_op_threshold = None
            total_amount_buyers = 0

        last_match_price_text = "LAST MATCH PRICE:\n" + (
            f"{self.last_match_price} AMD/RUB"
            if self.last_match_price
            else "No matches yet"
        )

        return {
            "data": {
                "currency_rate": self.currency_rate,
                "order_cnt": len(self._orders),
                "user_cnt": len(set([o.user.id for o in self._orders.values()])),
                "max_buyer_price": max_buyer_price,
                "max_buyer_min_op_threshold": max_buyer_min_op_threshold,
                "min_seller_price": min_seller_price,
                "min_seller_min_op_threshold": min_seller_min_op_threshold,
                "total_amount_sellers": total_amount_sellers,
                "total_amount_buyers": total_amount_buyers,
                "last_match_price": self.last_match_price,
            },
            "text": (
                f"Current exchange rate: {self.currency_rate['rate']} AMD/RUB on {self.currency_rate['date']}\n\n"
                f"{last_match_price_text}\n\n"
                f"BUYERS:\n"
                f"Total amount (all buyers): "
                f"{total_amount_buyers if total_amount_buyers < 1_000_000 else '1M+'} RUB\n"
                f"{max_buyer_text}\n\n"
                f"SELLERS:\n"
                f"Total amount (all sellers): "
                f"{total_amount_sellers if total_amount_sellers < 1_000_000 else '1M+'} RUB\n"
                f"{min_seller_text}"
            ),
            "short_text": (
                f"Current statistics (to get the full statistics, while being in main menu"
                " send '/stat' command or press Statistics button):\n"
                f"  * last match price: {self.last_match_price}\n"
                f"  * best buyer price: {max_buyer_price if buyers else 'No buyers yet'}\n"
                f"  * best seller price: {min_seller_price if sellers else 'No sellers yet'}"
            ),
        }

    def _log(self, operation: str, order: data.Order) -> None:
        if self._log_q:
            rec = data.Operation(data.OperationType.NEW_ORDER, order)
            self._log_q.send(pickle.dumps(rec))


class T(unittest.TestCase):
    pass
