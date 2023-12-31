import dataclasses
import enum
from decimal import Decimal
import unittest
import time


class OrderType(enum.IntEnum):
    SELL = 1
    BUY = 2


@dataclasses.dataclass
class User:
    id: int


@dataclasses.dataclass
class Order:
    user: User
    type: OrderType
    price: Decimal
    amount_initial: Decimal
    min_op_threshold: Decimal
    lifetime: Decimal  # Life time in hours
    creation_time: Decimal = dataclasses.field(default_factory=time.time)
    _id: int = None
    amount_left: Decimal = -1.0

    def __post_init__(self):
        if self.amount_left == -1.0:
            self.amount_left = self.amount_initial


@dataclasses.dataclass
class Match:
    sell_order: Order
    buy_order: Order
    price: Decimal
    amount: Decimal


class T(unittest.TestCase):
    def testT(self):
        pass
