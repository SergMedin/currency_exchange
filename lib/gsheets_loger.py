import threading
import zmq


class GSheetsLoger:

    def __init__(self, zmq_endpoint: str):
        self._sub_sock = zmq.Context.instance().socket(zmq.SUB)
        self._sub_sock.connect(zmq_endpoint)
        self._sub_sock.setsockopt(zmq.SUBSCRIBE, b'')
        threading.Thread(target=self._recv_forever).start()

    def _recv_forever(self):
        while True:
            s = self._sub_sock.recv_string()
            print("GOT_LOG:", s)
