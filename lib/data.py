import dataclasses
import enum
from decimal import Decimal
import unittest
import time
from typing import Optional


class OrderType(enum.IntEnum):
    SELL = 1
    BUY = 2


@dataclasses.dataclass
class User:
    id: int
    name: str = ""


@dataclasses.dataclass
class Order:
    """
    Represents an order in the currency exchange system.

    Attributes:
        user (User): The user who placed the order.
        type (OrderType): The type of the order (buy or sell).
        price (Decimal): The price at which the order is placed.
        amount_initial (Decimal): The initial amount of currency in the order.
        min_op_threshold (Decimal): The minimum operational threshold for the order.
        lifetime_sec (int): The lifetime of the order in seconds.
        creation_time (int, optional): The creation time of the order in seconds since the epoch.
        _id (int, optional): The unique identifier of the order.
        amount_left (Decimal, optional): The amount of currency left in the order.
    """

    user: User
    type: OrderType
    price: Decimal
    amount_initial: Decimal
    min_op_threshold: Decimal = Decimal(0.0)
    lifetime_sec: int = 48 * 60 * 60
    creation_time: int = dataclasses.field(default_factory=lambda: int(time.time()))
    _id: Optional[int] = None
    amount_left: Decimal = Decimal(-1.0)
    relative_rate: Decimal = Decimal(-1.0)  # -1.0 means not set; why not None?

    def __post_init__(self):
        if self.amount_left == -1.0:
            self.amount_left = self.amount_initial


@dataclasses.dataclass
class Match:
    """
    Represents a match between a sell order and a buy order in a currency exchange.
    """

    sell_order: Order
    buy_order: Order
    price: Decimal
    amount: Decimal


class OperationType(enum.StrEnum):
    NEW_ORDER = "new_order"
    UPDATE = "update"


@dataclasses.dataclass
class Operation:
    type: OperationType
    order: Order


class T(unittest.TestCase):
    def testT(self):
        pass
