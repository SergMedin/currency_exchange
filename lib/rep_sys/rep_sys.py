from dataclasses import dataclass
import time
from typing import Dict, Tuple
from unittest import TestCase, mock

from .rep_id import RepSysUserId
from .email_auth import EmailAuthenticator, EmailAuthenticatorMock


@dataclass
class AuthRecord:
    authenticated: bool
    when: float


AUTH_REC_VALIDITY_SEC = 60 * 60 * 24 * 30 * 3  # 90 days


class ReputationSystem:

    def is_authenticated(self, user_id: RepSysUserId) -> bool:
        try:
            rec = self._get_auth_record(user_id)
            return rec.authenticated and time.time() - rec.when < AUTH_REC_VALIDITY_SEC
        except KeyError:
            return False

    def set_authenticity(self, user_id: RepSysUserId, is_auth: bool) -> None:
        raise NotImplementedError()

    def get_email_authenticator(self, user_id: RepSysUserId) -> "EmailAuthenticator":
        raise NotImplementedError()

    def _get_auth_record(self, user_id: RepSysUserId) -> AuthRecord:
        raise NotImplementedError()


class RepSysMock(ReputationSystem):
    tg_auth: Dict[int, Tuple[bool, float]]

    def __init__(self):
        self.tg_auth = {}

    def set_authenticity(self, user_id: RepSysUserId, is_auth: bool) -> None:
        self.tg_auth[user_id.telegram_user_id] = (is_auth, time.time())

    def get_email_authenticator(self, user_id: RepSysUserId) -> "EmailAuthenticator":
        return EmailAuthenticatorMock(user_id)

    def _get_auth_record(self, user_id: RepSysUserId) -> AuthRecord:
        status, when = self.tg_auth[user_id.telegram_user_id]
        return AuthRecord(status, when)


class T(TestCase):

    def test_empty(self):
        rs = RepSysMock()
        self.assertFalse(rs.is_authenticated(RepSysUserId(123)))

    def test_auth(self):
        rs = RepSysMock()
        rs.set_authenticity(RepSysUserId(123), True)
        self.assertTrue(rs.is_authenticated(RepSysUserId(123)))

        rs.set_authenticity(RepSysUserId(123), False)
        self.assertFalse(rs.is_authenticated(RepSysUserId(123)))

    def test_expiration(self):
        rs = RepSysMock()
        rs.set_authenticity(RepSysUserId(123), True)
        self.assertTrue(rs.is_authenticated(RepSysUserId(123)))

        with mock.patch(
            "time.time", return_value=time.time() + AUTH_REC_VALIDITY_SEC + 1
        ):
            self.assertFalse(rs.is_authenticated(RepSysUserId(123)))
