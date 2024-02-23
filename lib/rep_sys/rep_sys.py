from typing import Dict
from unittest import TestCase

from .rep_id import RepSysUserId
from .email_auth import EmailAuthenticator, EmailAuthenticatorMock


class ReputationSystem:

    def is_authenticated(self, user_id: RepSysUserId) -> bool:
        raise NotImplementedError()

    def set_authenticity(self, user_id: RepSysUserId, is_auth: bool) -> None:
        raise NotImplementedError()

    def get_email_authenticator(self, user_id: RepSysUserId) -> "EmailAuthenticator":
        raise NotImplementedError()


class RepSysMock(ReputationSystem):
    tg_auth: Dict[int, bool]

    def __init__(self):
        self.tg_auth = {}

    def is_authenticated(self, user_id: RepSysUserId) -> bool:
        return self.tg_auth.get(user_id.telegram_user_id, False)

    def set_authenticity(self, user_id: RepSysUserId, is_auth: bool) -> None:
        self.tg_auth[user_id.telegram_user_id] = is_auth

    def get_email_authenticator(self, user_id: RepSysUserId) -> "EmailAuthenticator":
        return EmailAuthenticatorMock(user_id)


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
