from typing import Callable
import unittest
from sqlalchemy import create_engine
from .db import Db
from .data import Order


class SqlDb(Db):
    def __init__(self):
        self._eng = create_engine("sqlite://", echo=True)

    def get_order(self, id: int) -> Order:
        raise NotImplementedError()

    def store_order(self, o: Order) -> Order:
        raise NotImplementedError()

    def update_order(self, o: Order):
        raise NotImplementedError()

    def remove_order(self, id: int):
        raise NotImplementedError()

    def iterate_orders(self, callback: Callable[[Order], None]):
        raise NotImplementedError()


class T(unittest.TestCase):
    def testSimple(self):
        SqlDb()
