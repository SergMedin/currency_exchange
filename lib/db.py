import unittest
import dataclasses
import sqlite3
from decimal import Decimal
from typing import Callable, Any
from .data import Order, User, OrderType


class Db:
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


ValueConvertFunctionType = Callable[[Any,], Any]


@dataclasses.dataclass
class Field:
    do_name: str
    db_name: str
    ddl: str
    do2db: ValueConvertFunctionType = None
    db2do: ValueConvertFunctionType = None
    is_id: bool = False


@dataclasses.dataclass
class Table:
    name: str
    do_class: Callable
    fields: list[Field]

    def get_id_field(self) -> Field:
        return [f for f in self.fields if f.is_id][0]


class SQLiteDb(Db):
    # FIXME: use try..finally for cursors
    # FIXME: should we reuse cursor?
    # FIXME: add proper logging

    ORDERS_TABLE = Table("orders", Order, [
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
        id = self._store(self.ORDERS_TABLE, o)
        return self.get_order(id)

    def get_order(self, id: int) -> Order:
        return self._get(self.ORDERS_TABLE, id)

    def update_order(self, o: Order):
        self._update(self.ORDERS_TABLE, o)

    def remove_order(self, id: int):
        cursor = self._conn.cursor()
        cursor.execute(f"DELETE FROM {self.ORDERS_TABLE.name} WHERE id = ?", (id,))
        self._conn.commit()

    def iterate_orders(self, callback: Callable[[Order], None]):
        self._iterate(self.ORDERS_TABLE, callback)

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

    def _store(self, table: Table, do: Any) -> Any:
        db_fileds_list, values = self._get_insert_update_lists(table, do)
        db_fileds_list_str = ", ".join(db_fileds_list)
        question_marks = ", ".join(["?"] * len(db_fileds_list))
        sql = f"INSERT INTO {table.name} ({db_fileds_list_str}) VALUES ({question_marks})"
        # print("SQL:", sql, values)
        cursor = self._conn.cursor()
        cursor.execute(sql, values)
        _id = cursor.lastrowid
        self._conn.commit()
        return _id

    def _get(self, table: Table, id: Any) -> Any:
        idf = table.get_id_field()
        res = []
        self._iterate(table, lambda o: res.append(o), [f"{idf.db_name} = ?", (id,)])
        if not res:
            raise Exception(f"Row in {table.name} with id={id} was not found")
        return res[0]

    def _update(self, table: Table, do: Any):
        id_field = table.get_id_field()
        db_fileds_list, values = self._get_insert_update_lists(table, do)
        values.append(getattr(do, id_field.do_name))

        db_fileds_list_str = ", ".join([f"{field} = ?" for field in db_fileds_list])
        sql = f"UPDATE {self.ORDERS_TABLE.name} SET {db_fileds_list_str} WHERE id = ?"
        # print("SQL:", sql, values)
        cursor = self._conn.cursor()
        cursor.execute(sql, values)
        rc = cursor.rowcount
        self._conn.commit()
        if rc <= 0:
            raise Exception("Update statement didn't affect any row")

    def _get_insert_update_lists(self, table: Table, do: Any):
        db_fileds_list = []
        values = []
        for f in table.fields:
            if f.is_id:
                continue
            value_do = getattr(do, f.do_name)
            value_db = value_do if not f.do2db else f.do2db(value_do)
            db_fileds_list.append(f.db_name)
            values.append(value_db)
        return db_fileds_list, values

    def _mk_do_from_row(self, table: Table, row: sqlite3.Row) -> Any:
        row = dict(row)
        values = {}
        for f in table.fields:
            value = row[f.db_name] if not f.db2do else f.db2do(row[f.db_name])
            values[f.do_name] = value
        return table.do_class(**values)

    def _iterate(self, table: Table, callback: Callable[[Any], None], where: list[str, list] = None) -> None:
        cursor = self._conn.cursor()
        args = \
            [f"SELECT * FROM {table.name}"] if not where else \
            [f"SELECT * FROM {table.name} WHERE {where[0]}", where[1]]
        for row in cursor.execute(*args):
            do = self._mk_do_from_row(table, row)
            callback(do)


class T(unittest.TestCase):
    def testCtor(self):
        SQLiteDb(None)

    def testAddAndFetchOrder(self):
        db = SQLiteDb(None)
        o = Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48.0)
        o = db.store_order(o)
        self.assertEqual(OrderType.SELL, o.type)

    def testUpdate(self):
        db = SQLiteDb()
        o = Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48.0)
        o = db.store_order(o)
        o.price = Decimal("50.1")
        db.update_order(o)
        o = db.get_order(o._id)
        self.assertEqual(Decimal("50.1"), o.price)

    def testIterate(self):
        db = SQLiteDb()
        db.store_order(Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime=48.0))
        db.store_order(Order(User(2), OrderType.BUY, 95.0, 1299.0, 500.0, lifetime=48.0))
        orders = []
        db.iterate_orders(lambda o: orders.append(o))
        self.assertEqual(2, len(orders))
