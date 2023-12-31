import unittest
import dataclasses
import sqlite3
from decimal import Decimal
from typing import Callable, Any
from .data import Order, User, OrderType


class Db:
    def store_order(self, o: Order) -> Order:
        raise NotImplementedError()

    def remove_order(self, id: int):
        raise NotImplementedError()


class DbMock(Db):
    def __init__(self):
        self._order_id_gen = 0

    def store_order(self, o: Order) -> Order:
        self._order_id_gen += 1
        o = dataclasses.replace(o)
        o._id = self._order_id_gen
        return o

    def remove_order(self, id: int):
        pass


ValueConvertFunctionType = Callable[[Any,], Any]


@dataclasses.dataclass
class Field:
    do_name: str
    db_name: str
    ddl: str
    do2db: ValueConvertFunctionType = None
    db2do: ValueConvertFunctionType = None
    skip_insert: bool = False


@dataclasses.dataclass
class Table:
    name: str
    fields: list[Field]


class SQLiteDb(Db):
    # FIXME: use try..finally for cursors
    # FIXME: should we reuse cursor?

    ORDERS_TABLE = Table("orders", [
        Field("_id", "id", "INTEGER PRIMARY KEY", None, None, True),
        Field("type", "order_type", "INTEGER CHECK (order_type IN (1, 2))", lambda x: int(x), lambda x: OrderType(x)),
        Field("lifetime", "lifetime", "INTEGER NOT NULL"),
        Field("creation_time", "creation_time", "INTEGER NOT NULL"),
        Field("user", "user_id", "INTEGER NOT NULL", lambda x: x.id, lambda x: User(x)),
        Field("price", "price_cents",
              "INTEGER NOT NULL CHECK (price_cents > 0)", lambda x: int(x*100), lambda x: x/Decimal(100.0)),
        Field("amount_initial", "amount_initial_cents",
              "INTEGER NOT NULL CHECK (amount_initial_cents > 0)", lambda x: int(x*100), lambda x: x/Decimal(100.0)),
        Field("amount_left", "amount_left_cents", "INTEGER NOT NULL CHECK (amount_left_cents >= 0)",
              lambda x: int(x*100), lambda x: x/Decimal(100.0)),
        Field("min_op_threshold", "min_op_threshold_cents",
              "INTEGER NOT NULL CHECK (min_op_threshold_cents >= 0)", lambda x: int(x*100), lambda x: x/Decimal(100.0)),
    ])

    def __init__(self, filename=None):
        super().__init__()
        self._filename = filename or ":memory:"
        self._conn = sqlite3.connect(self._filename)
        self._conn.row_factory = sqlite3.Row
        self._ensure_db_initialized()

    def store_order(self, o: Order) -> Order:
        db_fileds_list = []
        values = []
        for f in self.ORDERS_TABLE.fields:
            if f.skip_insert:
                continue
            value_do = getattr(o, f.do_name)
            value_db = value_do if not f.do2db else f.do2db(value_do)
            db_fileds_list.append(f.db_name)
            values.append(value_db)

        db_fileds_list_str = ", ".join(db_fileds_list)
        question_marks = ", ".join(["?"] * len(db_fileds_list))
        sql = f"INSERT INTO {self.ORDERS_TABLE.name} ({db_fileds_list_str}) VALUES ({question_marks})"
        # print("SQL:", sql, values)
        cursor = self._conn.cursor()
        cursor.execute(sql, values)
        _id = cursor.lastrowid
        self._conn.commit()
        return self.get_order(_id)

    def get_order(self, id: int) -> Order:
        cursor = self._conn.cursor()
        cursor.execute(f"SELECT * FROM {self.ORDERS_TABLE.name} WHERE id = ?", (id,))
        row = cursor.fetchone()
        if not row:
            raise Exception(f"Order with id={id} not found in the DB")
        row = dict(row)
        # print("ROW:", row)
        values = {}
        for f in self.ORDERS_TABLE.fields:
            value = row[f.db_name] if not f.db2do else f.db2do(row[f.db_name])
            values[f.do_name] = value
        # print("VALUES:", row)
        return Order(**values)

    def remove_order(self, id: int):
        cursor = self._conn.cursor()
        cursor.execute(f"DELETE FROM {self.ORDERS_TABLE.name} WHERE id = ?", (id,))
        self._conn.commit()

    def _ensure_db_initialized(self):
        ddl = ", ".join(f"{f.db_name} {f.ddl}" for f in self.ORDERS_TABLE.fields)
        tables = [
            [self.ORDERS_TABLE.name, ddl]
        ]
        comm = False
        for table_name, ddl in tables:
            if not self._table_exists(table_name):
                cursor = self._conn.cursor()
                cursor.execute(f"CREATE TABLE {table_name} ({ddl})")
                comm = True
        if comm:
            self._conn.commit()

    def _table_exists(self, table_name):
        cursor = self._conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return bool(cursor.fetchone())


class T(unittest.TestCase):
    def testCtor(self):
        SQLiteDb(None)

    def testAddAndFetchOrder(self):
        db = SQLiteDb(None)
        o = Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48.0)
        db.store_order(o)
        # print("O2", o2)
