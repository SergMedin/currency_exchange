import dataclasses
from decimal import Decimal
from typing import Callable, Any
import unittest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session
from .db import Db
from .data import Order, OrderType, User


class SqlDb(Db):
    def __init__(self, conn_str: str = "sqlite://"):
        self._eng = create_engine(conn_str, echo=False)
        _Base.metadata.create_all(self._eng)

    def get_order(self, id: int) -> Order:
        return self._get(_ORDERS_TABLE, id)

    def store_order(self, o: Order) -> Order:
        return self._store(_ORDERS_TABLE, o)

    def update_order(self, o: Order):
        self._update(_ORDERS_TABLE, o)

    def remove_order(self, id: int):
        self._remove(_ORDERS_TABLE, id)

    def iterate_orders(self, callback: Callable[[Order], None]):
        self._iterate(_ORDERS_TABLE, callback)

    def _get(self, table, id):
        with Session(self._eng) as session:
            o = session.get(table.db_class, id)
            d = table.mk_dict(o, False)
        return table.do_class(**d)

    def _store(self, table, do):
        with Session(self._eng) as session:
            d = table.mk_dict(do, True)
            o_db = table.db_class(**d)
            session.add(o_db)
            session.commit()
            id = o_db.id
        return self._get(table, id)

    def _update(self, table, do):
        with Session(self._eng) as session:
            id = table.get_id(do)
            dbo = session.get(table.db_class, id)
            for field_name, value in table.mk_dict(do, True).items():
                setattr(dbo, field_name, value)  # updates only changed fields
            session.commit()

    def _remove(self, table, id):
        with Session(self._eng) as session:
            session.delete(session.get(table.db_class, id))
            session.commit()

    def _iterate(self, table, callback: Callable[[Order], None]):
        with Session(self._eng) as session:
            for dbo in session.scalars(select(table.db_class)):
                d = table.mk_dict(dbo, False)
                o = table.do_class(**d)
                callback(o)


class _Base(DeclarativeBase):
    pass


class _DbOrder(_Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[int] = mapped_column()
    lifetime_sec: Mapped[int] = mapped_column(nullable=False)
    creation_time: Mapped[int] = mapped_column(nullable=False)
    user: Mapped[str] = mapped_column(nullable=False)
    price_cents: Mapped[int] = mapped_column(nullable=False)
    amount_initial_cents: Mapped[int] = mapped_column(nullable=False)
    amount_left_cents: Mapped[int] = mapped_column(nullable=False)
    min_op_threshold_cents: Mapped[int] = mapped_column(nullable=False)


_ValueConvertFunctionType = Callable[
    [
        Any,
    ],
    Any,
]


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
    db_class: Callable
    get_id: Callable
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


def parse_user_data(user_data: str) -> User:
    if len(user_data.split(",")) != 2:
        raise ValueError(f"Invalid user data: [{user_data}]")
    id, name = user_data.split(",")
    return User(int(id), name)


_ORDERS_TABLE = _Table(
    Order,
    _DbOrder,
    lambda o: o._id,
    [
        _Field("_id", "id", None, None, True),
        _Field("type", "type", lambda x: int(x), lambda x: OrderType(x)),
        _Field("lifetime_sec", "lifetime_sec"),
        _Field("creation_time", "creation_time"),
        _Field(
            "user",
            "user",
            lambda x: f"{x.id},{x.name}",
            lambda x: parse_user_data(x),
        ),
        _Field(
            "price", "price_cents", lambda x: int(x * 100), lambda x: x / Decimal(100.0)
        ),
        _Field(
            "amount_initial",
            "amount_initial_cents",
            lambda x: int(x * 100),
            lambda x: x / Decimal(100.0),
        ),
        _Field(
            "amount_left",
            "amount_left_cents",
            lambda x: int(x * 100),
            lambda x: x / Decimal(100.0),
        ),
        _Field(
            "min_op_threshold",
            "min_op_threshold_cents",
            lambda x: int(x * 100),
            lambda x: x / Decimal(100.0),
        ),
    ],
)


class _T(unittest.TestCase):
    def setUp(self):
        self.db = SqlDb()

    def test_store_order(self):
        o = Order(
            User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60
        )
        o = self.db.store_order(o)
        self.assertEqual(OrderType.SELL, o.type)

    def test_update(self):
        o = Order(
            User(1, "Dima"),
            OrderType.SELL,
            98.0,
            1299.0,
            500.0,
            lifetime_sec=48 * 60 * 60,
        )
        o = self.db.store_order(o)
        o.price = Decimal("50.1")
        self.db.update_order(o)
        o = self.db.get_order(o._id)
        self.assertEqual(Decimal("50.1"), o.price)

    def test_iterate(self):
        self.db.store_order(
            Order(
                User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60
            )
        )
        self.db.store_order(
            Order(
                User(2), OrderType.BUY, 95.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60
            )
        )
        orders = []
        self.db.iterate_orders(lambda o: orders.append(o))
        self.assertEqual(2, len(orders))

    def test_remove(self):
        self.db.store_order(
            Order(
                User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60
            )
        )
        o = self.db.store_order(
            Order(
                User(2), OrderType.BUY, 95.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60
            )
        )
        self.db.remove_order(o._id)
        orders = []
        self.db.iterate_orders(lambda o: orders.append(o))
        self.assertEqual(1, len(orders))
