import dataclasses
from decimal import Decimal
from typing import Callable, Any
import unittest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session
from .db import Db
from .data import Order, OrderType, User


class SqlDb(Db):

    def __init__(self):
        self._eng = create_engine("sqlite://", echo=False)
        _Base.metadata.create_all(self._eng)

    def get_order(self, id: int) -> Order:
        with Session(self._eng) as session:
            o = session.get(_DbOrder, id)
            d = _ORDERS_TABLE.mk_dict(o, False)
        return Order(**d)

    def store_order(self, o: Order) -> Order:
        with Session(self._eng) as session:
            d = _ORDERS_TABLE.mk_dict(o, True)
            o_db = _DbOrder(**d)
            session.add(o_db)
            session.commit()
            id = o_db.id
        return self.get_order(id)

    def update_order(self, o: Order):
        with Session(self._eng) as session:
            dbo = session.get(_DbOrder, o._id)
            for field_name, value in _ORDERS_TABLE.mk_dict(o, True).items():
                setattr(dbo, field_name, value)  # updates only changed fields
            session.commit()

    def remove_order(self, id: int):
        with Session(self._eng) as session:
            session.delete(session.get(_DbOrder, id))
            session.commit()

    def iterate_orders(self, callback: Callable[[Order], None]):
        with Session(self._eng) as session:
            for dbo in session.scalars(select(_DbOrder)):
                d = _ORDERS_TABLE.mk_dict(dbo, False)
                o = Order(**d)
                callback(o)


class _Base(DeclarativeBase):
    pass


class _DbOrder(_Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[int] = mapped_column()
    lifetime: Mapped[int] = mapped_column(nullable=False)
    creation_time: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(nullable=False)
    price_cents: Mapped[int] = mapped_column(nullable=False)
    amount_initial_cents: Mapped[int] = mapped_column(nullable=False)
    amount_left_cents: Mapped[int] = mapped_column(nullable=False)
    min_op_threshold_cents: Mapped[int] = mapped_column(nullable=False)


_ValueConvertFunctionType = Callable[[Any,], Any]


@dataclasses.dataclass
class _Field:
    do_name: str
    db_name: str
    do2db: _ValueConvertFunctionType = None
    db2do: _ValueConvertFunctionType = None
    is_id: bool = False


@dataclasses.dataclass
class _Table:
    do_class: Callable  # FIXME: never used?
    fields: list[_Field]

    def get_id_field(self) -> _Field:
        return [f for f in self.fields if f.is_id][0]

    def mk_dict(self, obj: Any, is_do: bool) -> dict:
        d = {}
        for f in self.fields:
            from_field = f.do_name if is_do else f.db_name
            to_field = f.db_name if is_do else f.do_name
            conv = f.do2db if is_do else f.db2do
            value_from = getattr(obj, from_field)
            value = value_from if not conv else conv(value_from)
            d[to_field] = value
        return d


_ORDERS_TABLE = _Table(Order, [
    _Field("_id", "id", None, None, True),
    _Field("type", "type", lambda x: int(x), lambda x: OrderType(x)),
    _Field("lifetime", "lifetime"),
    _Field("creation_time", "creation_time"),
    _Field("user", "user_id", lambda x: x.id, lambda x: User(x)),
    _Field("price", "price_cents", lambda x: int(x*100), lambda x: x/Decimal(100.0)),
    _Field("amount_initial", "amount_initial_cents", lambda x: int(x*100), lambda x: x/Decimal(100.0)),
    _Field("amount_left", "amount_left_cents", lambda x: int(x*100), lambda x: x/Decimal(100.0)),
    _Field("min_op_threshold", "min_op_threshold_cents", lambda x: int(x*100), lambda x: x/Decimal(100.0)),
])


class _T(unittest.TestCase):
    def setUp(self):
        self.db = SqlDb()

    def test_store_order(self):
        o = Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48.0)
        o = self.db.store_order(o)
        self.assertEqual(OrderType.SELL, o.type)

    def test_update(self):
        o = Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48.0)
        o = self.db.store_order(o)
        o.price = Decimal("50.1")
        self.db.update_order(o)
        o = self.db.get_order(o._id)
        self.assertEqual(Decimal("50.1"), o.price)

    def test_iterate(self):
        self.db.store_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48.0))
        self.db.store_order(Order(User(2), OrderType.BUY, 95.0, 1299.0, 500.0, lifetime=48.0))
        orders = []
        self.db.iterate_orders(lambda o: orders.append(o))
        self.assertEqual(2, len(orders))

    def test_remove(self):
        self.db.store_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48.0))
        o = self.db.store_order(Order(User(2), OrderType.BUY, 95.0, 1299.0, 500.0, lifetime=48.0))
        self.db.remove_order(o._id)
        orders = []
        self.db.iterate_orders(lambda o: orders.append(o))
        self.assertEqual(1, len(orders))
