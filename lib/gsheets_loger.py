import threading
import zmq
import pickle
import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials
from .data import Order


class GSheetsLoger:
    _gapi_sheet = None
    _gapi_lock = threading.RLock()
    iii = 1

    def __init__(self, zmq_endpoint: str):
        self._stop_flag = False
        self._sub_sock = zmq.Context.instance().socket(zmq.SUB)
        self._sub_sock.connect(zmq_endpoint)
        self._sub_sock.setsockopt(zmq.SUBSCRIBE, b'')
        threading.Thread(target=self._recv_forever).start()

    def stop(self):
        self._stop_flag = True

    @classmethod
    def _get_sheet(cls):
        with cls._gapi_lock:
            if not cls._gapi_sheet:
                scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
                creds = ServiceAccountCredentials.from_json_keyfile_name('useful-mile-334600-ce60f5954ea9.json', scope)
                client = gspread.authorize(creds)
                cls._gapi_sheet = client.open('Curr Exchg Table').sheet1
            return cls._gapi_sheet

    def _add_record(self, operation: str, order: Order):
        with GSheetsLoger._gapi_lock:
            sheet = self._get_sheet()
            sheet.update_cell(GSheetsLoger.iii, 1, time.ctime(time.time()))
            sheet.update_cell(GSheetsLoger.iii, 2, operation)
            sheet.update_cell(GSheetsLoger.iii, 3, str(order))
            GSheetsLoger.iii += 1

    def _recv_forever(self):
        poller = zmq.Poller()
        poller.register(self._sub_sock, zmq.POLLIN)
        while not self._stop_flag:
            sockets = dict(poller.poll(300))
            if self._sub_sock in sockets:
                data = self._sub_sock.recv()
                rec = pickle.loads(data)
                operation = rec["operation"]
                order = rec["order"]
                print("GOT_LOG:", operation, order)
                self._add_record(operation, order)
        self._sub_sock.close()
