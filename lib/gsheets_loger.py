import threading
import zmq
import pickle
import time
import os
import unittest
from .data import Operation, Order, OrderType, OperationType, User
from .gspreads import GSpreadsTable, GSpreadsTableMock


class GSheetsLoger:
    _lock = threading.RLock()
    iii = 1

    def __init__(self, zmq_endpoint: str, spreadsheet_key=None, sheet_title=None):
        self._stop_flag = False
        self._sub_sock = zmq.Context.instance().socket(zmq.SUB)
        self._sub_sock.connect(zmq_endpoint)
        self._sub_sock.setsockopt(zmq.SUBSCRIBE, b'')
        self._thread: threading.Thread = None
        if spreadsheet_key:
            credentials_filepath = os.getenv("GCLOUD_ACC_CREDENTIALS_FILE", "useful-mile-334600-ce60f5954ea9.json")
            self._gst = GSpreadsTable(credentials_filepath, spreadsheet_key, sheet_title)
        else:
            self._gst = GSpreadsTableMock()

    def __del__(self):
        if self._thread:
            self.stop()
        self._sub_sock.close()

    def start(self):
        self._thread = threading.Thread(target=self._recv_forever)
        self._thread.start()

    def stop(self):
        self._stop_flag = True
        if self._thread:
            self._thread.join()
            self._thread = None

    def _add_record(self, op: Operation):
        with GSheetsLoger._lock:
            sheet = self._gst
            range_name = f"A{GSheetsLoger.iii}"
            o = op.order
            row = [
                time.ctime(time.time()),
                op.type,
                o._id,
                o.user.id,
                o.user.name,
                o.type.name,
                float(o.price),  # FIXME: learn the right way to make correct decimal values in Google Sheets
                float(o.amount_initial),
                float(o.amount_left),
                float(o.min_op_threshold),
                o.lifetime_sec / 3600.0,
            ]
            sheet.update(range_name, [row])
            GSheetsLoger.iii += 1

    def _recv_forever(self):
        poller = zmq.Poller()
        poller.register(self._sub_sock, zmq.POLLIN)
        while not self._stop_flag:
            sockets = dict(poller.poll(100))
            if self._sub_sock in sockets:
                data = self._sub_sock.recv()
                op: Operation = pickle.loads(data)
                self._add_record(op)


class T(unittest.TestCase):

    def test_simple(self):
        log = GSheetsLoger("inproc://test")
        o = Order(User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48*60*60)
        op = Operation(OperationType.NEW_ORDER, o)
        log._add_record(op)
        t = log._gst
        self.assertEqual(t.cell(1, 2), "new_order")
        self.assertEqual(t.cell(1, 4), 1)
        self.assertEqual(t.cell(1, 6), "SELL")
