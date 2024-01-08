import dataclasses
import enum
from decimal import Decimal
import unittest


class OrderState(enum.StrEnum):
    DRAFT = "draft"
    PLACED = "placed"
    WAIT_DELIVERY = "wait_delivery"
    CLOSED = "closed"


@dataclasses.dataclass
class Order:
    state: OrderState = OrderState.DRAFT
    id: int = None
    price: Decimal = None


class T(unittest.TestCase):
    def testT(self):
        pass
