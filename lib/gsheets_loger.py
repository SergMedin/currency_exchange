import threading
import zmq


class GSheetsLoger:

    def __init__(self, zmq_endpoint: str):
        self._stop_flag = False
        self._sub_sock = zmq.Context.instance().socket(zmq.SUB)
        self._sub_sock.connect(zmq_endpoint)
        self._sub_sock.setsockopt(zmq.SUBSCRIBE, b'')
        threading.Thread(target=self._recv_forever).start()

    def stop(self):
        self._stop_flag = True

    def _recv_forever(self):
        poller = zmq.Poller()
        poller.register(self._sub_sock, zmq.POLLIN)
        while not self._stop_flag:
            sockets = dict(poller.poll(300))
            if self._sub_sock in sockets:
                s = self._sub_sock.recv_string()
                print("GOT_LOG:", s)
        self._sub_sock.close()
