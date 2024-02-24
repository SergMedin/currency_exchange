import time
from typing import Any
from unittest import TestCase, mock


from .rep_sys_db import RepSysDb
from .rep_id import RepSysUserId
from .auth_rec import AuthRecord


AUTH_REC_VALIDITY_SEC = 60 * 60 * 24 * 30 * 3  # 90 days


class ReputationSystem:
    def __init__(self, db_engine: Any):
        self._db_engine = db_engine
        self._db = RepSysDb(db_engine)

    def is_authenticated(self, user_id: RepSysUserId) -> bool:
        try:
            rec = self._get_auth_record(user_id)
            return rec.authenticated and time.time() - rec.when < AUTH_REC_VALIDITY_SEC
        except KeyError:
            return False

    def set_authenticity(self, user_id: RepSysUserId, is_auth: bool) -> None:
        self._db.set_authenticity(user_id.telegram_user_id, is_auth)

    def _get_auth_record(self, user_id: RepSysUserId) -> AuthRecord:
        return self._db.get_auth_record(user_id.telegram_user_id)


class T(TestCase):
    def setUp(self):
        import sqlalchemy

        self.db_engine = sqlalchemy.create_engine("sqlite://")
        self.rs = ReputationSystem(self.db_engine)

    def test_empty(self):
        self.assertFalse(self.rs.is_authenticated(RepSysUserId(123)))

    def test_auth(self):
        self.rs.set_authenticity(RepSysUserId(123), True)
        self.assertTrue(self.rs.is_authenticated(RepSysUserId(123)))

        self.rs.set_authenticity(RepSysUserId(123), False)
        self.assertFalse(self.rs.is_authenticated(RepSysUserId(123)))

    def test_expiration(self):
        self.rs.set_authenticity(RepSysUserId(123), True)
        self.assertTrue(self.rs.is_authenticated(RepSysUserId(123)))

        with mock.patch(
            "time.time", return_value=time.time() + AUTH_REC_VALIDITY_SEC + 1
        ):
            self.assertFalse(self.rs.is_authenticated(RepSysUserId(123)))
