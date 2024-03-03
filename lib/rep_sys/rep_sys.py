import time
from typing import Any, Optional
from unittest import TestCase, mock


from .rep_sys_db import RepSysDb
from .rep_id import RepSysUserId
from .auth_rec import AuthRecord


AUTH_REC_VALIDITY_SEC = 60 * 60 * 24 * 30 * 3  # 90 days


class ReputationSystem:
    def __init__(self, db_engine: Any):
        self._db_engine = db_engine
        self._db = RepSysDb(db_engine)

    def is_authenticated(self, uid: RepSysUserId) -> bool:
        try:
            rec = self._db.get_auth_record(uid)
            return rec.authenticated and time.time() - rec.when < AUTH_REC_VALIDITY_SEC
        except KeyError:
            return False

    def enrich_user_id(self, uid: RepSysUserId) -> RepSysUserId:
        try:
            rec = self._db.get_auth_record(uid)
            return rec.uid
        except KeyError:
            return uid

    def is_id_consistent(self, uid: RepSysUserId) -> bool:
        assert uid.telegram_user_id and uid.email_hash
        ids = [
            RepSysUserId(telegram_user_id=uid.telegram_user_id),
            RepSysUserId(email_hash=uid.email_hash),
        ]
        recs: list[Optional[AuthRecord]] = []
        for id in ids:
            try:
                recs.append(self._db.get_auth_record(id))
            except KeyError:
                recs.append(None)
        rec1, rec2 = recs

        if (rec1 and rec1.uid != uid) or (rec2 and rec2.uid != uid):
            return False
        return True

    def set_authenticity(self, uid: RepSysUserId, is_auth: bool) -> None:
        if uid.telegram_user_id and uid.email_hash and not self.is_id_consistent(uid):
            raise ValueError("Inconsistent user id")
        self._db.set_authenticity(uid, is_auth)


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

    def test_consistency(self):
        self.rs.set_authenticity(RepSysUserId(123, "hash"), True)
        self.assertTrue(self.rs.is_authenticated(RepSysUserId(123)))
        self.assertTrue(self.rs.is_authenticated(RepSysUserId(None, "hash")))
        self.assertTrue(self.rs.is_id_consistent(RepSysUserId(123, "hash")))
        self.assertFalse(self.rs.is_id_consistent(RepSysUserId(555, "hash")))

    def test_consistency2(self):
        self.rs.set_authenticity(RepSysUserId(123, "hash"), True)
        self.assertRaises(
            ValueError, self.rs.set_authenticity, RepSysUserId(555, "hash"), True
        )
        self.assertRaises(
            ValueError, self.rs.set_authenticity, RepSysUserId(123, "hash2"), True
        )

    def test_enrichment(self):
        self.rs.set_authenticity(RepSysUserId(123, "hash"), True)
        id1 = self.rs.enrich_user_id(RepSysUserId(123))
        self.assertEqual(123, id1.telegram_user_id)
        self.assertEqual("hash", id1.email_hash)
