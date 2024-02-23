from enum import Enum
import logging
from typing import Optional
import random
from unittest import TestCase
from .rep_id import RepSysUserId
from lib.comms.mailer import EmailAddress, Mailer, MailerMock


_MAX_ATTEMPTS = 3


class EmailAuthenticator:
    def __init__(
        self, user_id: RepSysUserId, mailer: Mailer, max_attempts: int = _MAX_ATTEMPTS
    ):
        self._user_id = user_id
        self._mailer = mailer
        self._state = EmlAuthState.WAIT_EMAIL
        self._code: Optional[str] = None
        self._email: Optional[str] = None
        self._attempts: int = 0
        self._max_attempts = max_attempts
        # TODO: add rate limiter for emails and codes

    @property
    def state(self) -> "EmlAuthState":
        return self._state

    def send_email(self, email: str):
        if not EmailAddress(email).is_valid:
            raise ValueError(f"Invalid email {email}")
        self._email = email
        self._code = self._renerate_rnd_code()
        self._mailer.send_email(EmailAddress(email), f"Your code is {self._code}")
        logging.info(f"Sent code {self._code} to {email}")
        self._state = EmlAuthState.WAIT_CODE

    def reset(self):
        self._state = EmlAuthState.WAIT_EMAIL
        self._email = None
        self._code = None
        self._attempts = 0

    def is_code_valid(self, code: str) -> bool:
        if self._state != EmlAuthState.WAIT_CODE:
            raise RuntimeError("Invalid state for code validation")
        self._attempts += 1
        if self._attempts > self._max_attempts:
            self._state = EmlAuthState.WAIT_EMAIL
            self._attempts = 0
            raise TooManyAttemptsError()
        return code == self._code

    @classmethod
    def _renerate_rnd_code(cls) -> str:
        return str(random.randint(1000, 9999))


class EmlAuthState(Enum):
    WAIT_EMAIL = 1
    WAIT_CODE = 2


class TooManyAttemptsError(Exception):
    pass


# TODO: add persistence
class EmailAuthenticatorReal(EmailAuthenticator):
    def __init__(self, user_id: RepSysUserId, mailer: Mailer):
        super().__init__(user_id, mailer)

    def send_email(self, email: str):
        super().send_email(email)
        # TODO: do some real shit; save in DB: state, email, code
        raise NotImplementedError()


class EmailAuthenticatorMock(EmailAuthenticator):
    def __init__(self, user_id: RepSysUserId):
        self.mm = MailerMock()
        super().__init__(user_id, self.mm)


class T(TestCase):
    def setUp(self) -> None:
        self.au = EmailAuthenticatorMock(RepSysUserId(123))
        self.mm = self.au.mm
        return super().setUp()

    def test_ctor(self):
        self.assertEqual(EmlAuthState.WAIT_EMAIL, self.au.state)

    def test_happy_path(self):
        self.au.send_email("john@example.net")
        self.assertEqual(EmlAuthState.WAIT_CODE, self.au.state)
        self.assertEqual(1, len(self.mm.sent))
        self.assertIn(self.au._code, self.mm.sent[EmailAddress("john@example.net")][0])

        res = self.au.is_code_valid(self.au._code)
        self.assertTrue(res)

    def test_wrong_code(self):
        self.au.send_email("john@example.net")
        res = self.au.is_code_valid("wrongcode")
        self.assertFalse(res)

    def test_attempts_limiter(self):
        self.au.send_email("john@example.net")
        self.au.is_code_valid("wrongcode")
        self.au.is_code_valid("wrongcode")
        self.au.is_code_valid("wrongcode")
        self.assertRaises(TooManyAttemptsError, self.au.is_code_valid, "wrongcode")
