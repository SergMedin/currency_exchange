import unittest
import dataclasses
import sqlite3
from .data import Order


class Db:
    def store_order(self, o: Order) -> Order:
        raise NotImplementedError()

    def remove_order(self, _id: int):
        raise NotImplementedError()


class DbMock(Db):
    def __init__(self):
        self._order_id_gen = 0

    def store_order(self, o: Order) -> Order:
        self._order_id_gen += 1
        o = dataclasses.replace(o)
        o._id = self._order_id_gen
        return o

    def remove_order(self, _id: int):
        pass


class SQLiteDb(Db):
    ORDERS_TABLE_NAME = "orders"

    def __init__(self, filename=None):
        super().__init__()
        self._filename = filename or ":memory:"
        self._conn = sqlite3.connect(self._filename)
        self._ensure_db_initialized()

    def _ensure_db_initialized(self):
        ddl = """
            id INTEGER PRIMARY KEY,
            order_type INTEGER CHECK (order_type IN (1, 2)),
            seller_id INEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            amount_initial_cents INTEGER NOT NULL CHECK (amount_initial_cents > 0),
            amount_left_cents INTEGER NOT NULL CHECK (amount_left_cents >= 0),
            min_op_threshold_cents INTEGER NOT NULL CHECK (min_op_threshold_cents >= 0)
            """
        tables = [
            [self.ORDERS_TABLE_NAME, ddl]
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
