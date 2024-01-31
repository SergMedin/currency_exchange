import threading
import zmq
import pickle
import time
import os
import unittest
import logging
from .data import Operation, Order, OrderType, OperationType, User
from .gspreads import GSpreadsTable, GSpreadsTableMock


# TODO:
# - Detect empty worksheet and set it up with correct column names
# - Create new worksheet for every new month


class GSheetsLoger:

    def __init__(self, zmq_endpoint: str, spreadsheet_key=None, sheet_title=None):
        self._curr_row = None
        self._stop_flag = False
        self._sub_sock = zmq.Context.instance().socket(zmq.SUB)
        self._sub_sock.connect(zmq_endpoint)
        self._sub_sock.setsockopt(zmq.SUBSCRIBE, b"")
        self._thread: threading.Thread = None
        if spreadsheet_key:
            credentials_filepath = os.getenv(
                "GCLOUD_ACC_CREDENTIALS_FILE", "useful-mile-334600-ce60f5954ea9.json"
            )
            logging.info("Using GSpreadsTable")
            self._gst = GSpreadsTable(
                credentials_filepath, spreadsheet_key, sheet_title
            )
        else:
            logging.info("Using GSpreadsTableMock")
            self._gst = GSpreadsTableMock()
        self._check_and_setup_sheet()

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
        sheet = self._gst
        range_name = f"A{self._curr_row}"
        self._curr_row += 1
        o = op.order
        row = [
            time.ctime(time.time()),
            op.type,
            o._id,
            o.user.id,
            o.user.name,
            o.type.name,
            float(
                o.price
            ),  # FIXME: learn the right way to make correct decimal values in Google Sheets
            float(o.amount_initial),
            float(o.amount_left),
            float(o.min_op_threshold),
            o.lifetime_sec / 3600.0,
        ]
        logging.info(f"Adding record at [{range_name}]: {row}")
        sheet.update(range_name, [row])

    def _setup_header_row(self):
        row = [
            "date",
            "op_type",
            "order_id",
            "user_id",
            "user_name",
            "order_type",
            "price",
            "amount_initial",
            "amount_left",
            "min_op_threshold",
            "lifetime",
        ]
        self._gst.update("A1", [row])
        self._gst.freeze(1)

    def _check_and_setup_sheet(self):
        if not self._curr_row:
            self._curr_row = self._gst.next_available_row()
            if self._curr_row == 1:
                logging.info("Empty worksheet detected. Adding headers")
                self._setup_header_row()
                self._curr_row = 2
            logging.info(f"Adding records from row {self._curr_row}")

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
    # def setUp(self) -> None:
    #     logging.basicConfig(level=logging.INFO)

    def test_simple(self):
        log = GSheetsLoger("inproc://test")
        o = Order(
            User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60
        )
        op = Operation(OperationType.NEW_ORDER, o)
        log._add_record(op)
        t = log._gst
        self.assertEqual(t.cell(1, 1), "date")
        self.assertEqual(t.cell(1, 2), "op_type")
        self.assertEqual(t.cell(1, 3), "order_id")
        self.assertEqual(t.cell(2, 2), "new_order")
        self.assertEqual(t.cell(2, 4), 1)
        self.assertEqual(t.cell(2, 6), "SELL")

    def test_append(self):
        log = GSheetsLoger("inproc://test")
        log._gst.update_cell(2, 1, "this line is not empty")
        log._curr_row = None
        log._check_and_setup_sheet()

        o = Order(
            User(1), OrderType.SELL, 98.0, 1299.0, 500.0, lifetime_sec=48 * 60 * 60
        )
        op = Operation(OperationType.NEW_ORDER, o)
        log._add_record(op)
        t = log._gst
        self.assertEqual(t.cell(3, 2), "new_order")
        self.assertEqual(t.cell(3, 4), 1)
        self.assertEqual(t.cell(3, 6), "SELL")
