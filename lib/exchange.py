import unittest
import dataclasses
from .db import Db
from . import data


class Exchange:

    def __init__(self, db: Db, on_match=None):
        self._db = db
        self._on_match = on_match
        self._orders = []  # TODO: load orders from db here

    def on_new_order(self, o: data.Order):
        self._orders.append(dataclasses.replace(o))

        # TODO: find matches here


class T(unittest.TestCase):
    pass
