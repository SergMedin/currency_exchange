import dataclasses
import enum


class OrderType(enum.Enum):
    SELL = 1
    BUY = 2


@dataclasses.dataclass
class User:
    id: int


@dataclasses.dataclass
class Order:
    user: User
    type: OrderType
    amount_initial: int
    amount_left: int
    min_op_threshold: int
