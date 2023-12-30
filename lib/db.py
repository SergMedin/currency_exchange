import unittest
import dataclasses
from .data import Order


class Db:
    def store_order(self, o: Order) -> Order:
        raise NotImplementedError()

    def remove_order(self, _id: int):
        raise NotImplementedError()


class DbMock(Db):
    def __init__(self):
        self._order_id_gen = 0

    def store_order(self, o: Order) -> Order:
        self._order_id_gen += 1
        o = dataclasses.replace(o)
        o._id = self._order_id_gen
        return o

    def remove_order(self, _id: int):
        pass


class T(unittest.TestCase):
    pass
