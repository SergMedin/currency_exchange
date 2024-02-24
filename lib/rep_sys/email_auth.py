from dataclasses import dataclass, field
from enum import Enum
import logging
import time
from typing import Optional
import random
from unittest import mock
from unittest import TestCase
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session
from .rep_id import RepSysUserId
from lib.comms.mailer import EmailAddress, Mailer, MailerMock


_MAX_ATTEMPTS = 3
_STATE_VALIDITY_SEC = 60 * 60 * 1  # 1 hour


class EmailAuthenticator:
    @dataclass
    class State:
        ctime: int = field(default_factory=lambda: int(time.time()))
        state: "EmlAuthState" = field(default_factory=lambda: EmlAuthState.WAIT_EMAIL)
        code: Optional[str] = None
        email: Optional[str] = None
        attempts: int = 0

    def __init__(
        self,
        user_id: RepSysUserId,
        mailer: Mailer,
        db_eng: Engine,
        max_attempts: int = _MAX_ATTEMPTS,
    ):
        self._mailer = mailer
        self._max_attempts = max_attempts
        self._db_eng = db_eng
        self._user_id = user_id
        self._pers = EmailAuthenticator.State()

        _Base.metadata.create_all(self._db_eng)
        self._load_state()

    @property
    def state(self) -> "EmlAuthState":
        return self._pers.state

    def send_email(self, email: str):
        if not EmailAddress(email).is_valid:
            raise ValueError(f"Invalid email {email}")

        code = self._renerate_rnd_code()

        logging.info(f"Sending code {code} to {email} ...")
        try:
            self._mailer.send_email(EmailAddress(email), f"Your code is {code}")
        except Exception as e:
            logging.exception(f"Failed to send code to {email}: {e}")
            raise
        logging.info(f"Sent code {code} to {email}")

        self._pers.email = email
        self._pers.code = code
        self._pers.state = EmlAuthState.WAIT_CODE
        self._save_state()

    def reset(self):
        self.delete()
        self._load_state()

    def is_code_valid(self, code: str) -> bool:
        if self._pers.state != EmlAuthState.WAIT_CODE:
            raise RuntimeError("Invalid state for code validation")

        if time.time() - self._pers.ctime > _STATE_VALIDITY_SEC:
            self.reset()
            raise TooManyAttemptsOrExpiredError()

        try:
            self._pers.attempts += 1
            if self._pers.attempts > self._max_attempts:
                self.reset()
                raise TooManyAttemptsOrExpiredError()
            return code == self._pers.code
        finally:
            self._save_state()

    def delete(self):
        with Session(self._db_eng) as session:
            dbo = session.get(_EmailAuthState, self._user_id.telegram_user_id)
            if dbo:
                session.delete(dbo)
                session.commit()
                logging.info(f"Deleted state for {self._user_id.telegram_user_id}")

    def _load_state(self):
        self._pers = EmailAuthenticator.State()
        with Session(self._db_eng) as session:
            dbo = session.get(_EmailAuthState, self._user_id.telegram_user_id)
            if dbo is None:
                dbo = _EmailAuthState(
                    telegram_user_id=self._user_id.telegram_user_id,
                    ctime=self._pers.ctime,
                    state=self._pers.state.value,
                    attempts=self._pers.attempts,
                )
                session.add(dbo)
            self._pers.ctime = dbo.ctime
            self._pers.state = EmlAuthState(dbo.state)
            self._pers.code = dbo.code
            self._pers.email = dbo.email
            self._pers.attempts = dbo.attempts
            session.commit()

    def _save_state(self):
        try:
            with Session(self._db_eng) as session:
                dbo = session.get(_EmailAuthState, self._user_id.telegram_user_id)
                assert dbo
                dbo.state = self._pers.state.value
                dbo.email = self._pers.email
                dbo.code = self._pers.code
                dbo.attempts = self._pers.attempts
                session.commit()
        except Exception as e:
            logging.exception(f"Failed to save state: {e}")
            raise

    @classmethod
    def _renerate_rnd_code(cls) -> str:
        return str(random.randint(1000, 9999))


class EmlAuthState(Enum):
    WAIT_EMAIL = 1
    WAIT_CODE = 2


class TooManyAttemptsOrExpiredError(Exception):
    pass


class _Base(DeclarativeBase):
    pass


class _EmailAuthState(_Base):
    __tablename__ = "email_auth_states"

    telegram_user_id: Mapped[int] = mapped_column(primary_key=True)
    ctime: Mapped[int] = mapped_column(nullable=False)
    state: Mapped[int] = mapped_column(nullable=False)
    attempts: Mapped[int] = mapped_column(nullable=False)
    code: Mapped[Optional[str]] = mapped_column()
    email: Mapped[Optional[str]] = mapped_column()


class T(TestCase):
    def setUp(self) -> None:
        self.mm = MailerMock()
        self.eng = create_engine("sqlite://")
        self.au = EmailAuthenticator(RepSysUserId(123), self.mm, self.eng)
        return super().setUp()

    def test_ctor(self):
        self.assertEqual(EmlAuthState.WAIT_EMAIL, self.au.state)

    def test_happy_path(self):
        self.au.send_email("john@example.net")
        self.assertEqual(EmlAuthState.WAIT_CODE, self.au.state)
        self.assertEqual(1, len(self.mm.sent))
        self.assertIn(
            self.au._pers.code, self.mm.sent[EmailAddress("john@example.net")][0]
        )

        res = self.au.is_code_valid(self.au._pers.code)
        self.assertTrue(res)

    def test_persistence(self):
        self.au.send_email("john@example.net")
        del self.au
        other = EmailAuthenticator(RepSysUserId(123), self.mm, self.eng)
        res = other.is_code_valid(other._pers.code)
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
        self.assertRaises(
            TooManyAttemptsOrExpiredError, self.au.is_code_valid, "wrongcode"
        )

    def test_reset(self):
        self.au.send_email("john@example.net")
        self.assertEqual(EmlAuthState.WAIT_CODE, self.au.state)
        self.assertEqual(1, len(self.mm.sent))
        self.assertIn(
            self.au._pers.code, self.mm.sent[EmailAddress("john@example.net")][0]
        )

        self.au.reset()
        self.assertEqual(EmlAuthState.WAIT_EMAIL, self.au.state)

    def test_state_expiration(self):
        self.au.send_email("john@example.net")
        res = self.au.is_code_valid(self.au._pers.code)
        self.assertTrue(res)

        with mock.patch(
            "time.time", return_value=time.time() + _STATE_VALIDITY_SEC + 1
        ):
            self.assertRaises(
                TooManyAttemptsOrExpiredError, self.au.is_code_valid, self.au._pers.code
            )
