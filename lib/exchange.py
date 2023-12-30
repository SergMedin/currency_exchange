import dataclasses
import unittest
from .db import Db
from . import data


class Exchange:

    def __init__(self, db: Db, on_match=None):
        self._db = db
        self._on_match = on_match
        self._orders: dict[int, data.Order] = {}  # TODO: load orders from db here

    def on_new_order(self, o: data.Order):
        o = self._db.store_order(o)
        self._orders[o._id] = o
        self._process_matches()

    def _process_matches(self):
        while True:
            sellers, buyers = [[o for o in self._orders.values() if o.type == t]
                               for t in [data.OrderType.SELL, data.OrderType.BUY]]

            # print("S, B:", sellers, buyers)

            if len(sellers) <= 0 or len(buyers) <= 0:
                break

            sellers.sort(key=lambda x: x.price)
            buyers.sort(key=lambda x: -x.price)

            so = sellers[0]
            bo = buyers[0]
            if bo.price >= so.price:  # FIXME: it now ignores min_thershold
                amount = min(bo.amount_left, so.amount_left)
                match = data.Match(dataclasses.replace(so), dataclasses.replace(bo), so.price, amount)
                if self._on_match:
                    self._on_match(match)
                so.amount_left -= amount
                bo.amount_left -= amount
                for o in (so, bo):
                    if o.amount_left <= 0:
                        self._remove_order(o._id)
            else:
                break

    def _remove_order(self, _id: int):
        del self._orders[_id]
        self._db.remove_order(_id)


class T(unittest.TestCase):
    pass
