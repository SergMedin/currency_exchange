from transitions import Machine
from enum import Enum
import time
from unittest import TestCase
from .data import Order


class SessionState(Enum):
    INITIAL = 0
    IDLE = 1
    ORDERING = 2
    CANCELING = 3
    DELETED = 999


class UserSession(Machine):
    TIMEOUT = 60 * 60

    def __init__(self, user_id: int, time_provider=time.time):
        self._user_id = user_id
        self._orders = 0
        self._t = time_provider
        self._mtime = self._t()
        Machine.__init__(self, states=SessionState, initial="INITIAL")
        self.add_transition("hello", SessionState.INITIAL, SessionState.IDLE)
        self.add_transition(
            "start_order",
            SessionState.IDLE,
            SessionState.ORDERING,
            conditions="can_order",
        )
        self.add_transition(
            "place_order",
            SessionState.ORDERING,
            SessionState.IDLE,
            after="on_order_placed",
        )
        self.add_transition("calcel_order", SessionState.IDLE, SessionState.CANCELING)
        self.add_transition("confirm_cancel", SessionState.CANCELING, SessionState.IDLE)
        self.add_transition("delete", "*", SessionState.DELETED)
        self.add_transition(
            "timeout",
            [SessionState.ORDERING, SessionState.CANCELING],
            SessionState.IDLE,
            conditions="timeouted",
            after="on_timeout",
        )

    def on_enter_IDLE(self):
        # print("Entering IDLE")
        pass

    def on_enter_ORDERING(self):
        # print("Placing an order")
        pass

    def on_order_placed(self):
        self._orders += 1

    def on_timeout(self):
        # do some cleanup work
        pass

    @property
    def active_orders_count(self) -> int:
        return self._orders

    @property
    def timeouted(self):
        return self._t() - self._mtime > self.TIMEOUT

    @property
    def can_order(self) -> bool:
        return self.active_orders_count <= 0


class T(TestCase):
    def test_simple(self):
        us = UserSession(123)
        us.hello()
        self.assertEqual(us.state, SessionState.IDLE)
        us.start_order()
        us.place_order()
        self.assertFalse(us.may_start_order())

    def test_delete(self):
        us = UserSession(123)
        us.hello()
        us.delete()
        self.assertEqual(us.state, SessionState.DELETED)

    def test_temeout(self):
        d = {"t": 0}
        us = UserSession(123, time_provider=lambda: d["t"])
        us.hello()
        us.start_order()
        self.assertEqual(us.state, SessionState.ORDERING)
        d["t"] = 60 * 30
        us.timeout()
        self.assertEqual(us.state, SessionState.ORDERING)
        d["t"] = 60 * 60 + 1
        us.timeout()
        self.assertEqual(us.state, SessionState.IDLE)
