from enum import Enum
import logging
from typing import Optional
import random
from unittest import TestCase
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session
from .rep_id import RepSysUserId
from lib.comms.mailer import EmailAddress, Mailer, MailerMock


_MAX_ATTEMPTS = 3


class EmailAuthenticator:
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
        self._state = EmlAuthState.WAIT_EMAIL
        self._code: Optional[str] = None
        self._email: Optional[str] = None
        self._attempts: int = 0

        _Base.metadata.create_all(self._db_eng)
        self._load_state()

    @property
    def state(self) -> "EmlAuthState":
        return self._state

    def send_email(self, email: str):
        if not EmailAddress(email).is_valid:
            raise ValueError(f"Invalid email {email}")

        code = self._renerate_rnd_code()

        logging.info(f"Sending code {self._code} to {email} ...")
        try:
            self._mailer.send_email(EmailAddress(email), f"Your code is {code}")
        except Exception as e:
            logging.exception(f"Failed to send code to {email}: {e}")
            raise
        logging.info(f"Sent code {self._code} to {email}")

        self._email = email
        self._code = code
        self._state = EmlAuthState.WAIT_CODE
        self._save_state()

    def reset(self):
        self._state = EmlAuthState.WAIT_EMAIL
        self._email = None
        self._code = None
        self._attempts = 0
        self._save_state()

    def is_code_valid(self, code: str) -> bool:
        if self._state != EmlAuthState.WAIT_CODE:
            raise RuntimeError("Invalid state for code validation")
        try:
            self._attempts += 1
            if self._attempts > self._max_attempts:
                self._state = EmlAuthState.WAIT_EMAIL
                self._attempts = 0
                raise TooManyAttemptsError()
            return code == self._code
        finally:
            self._save_state()

    def _load_state(self):
        with Session(self._db_eng) as session:
            dbo = session.get(_EmailAuthState, self._user_id.telegram_user_id)
            if dbo is None:
                dbo = _EmailAuthState(
                    telegram_user_id=self._user_id.telegram_user_id,
                    state=self._state.value,
                )
                session.add(dbo)
                session.commit()
            else:
                self._state = EmlAuthState(dbo.state)
                self._code = dbo.code
                self._email = dbo.email
                self._attempts = dbo.attempts

    def _save_state(self):
        try:
            with Session(self._db_eng) as session:
                dbo = session.get(_EmailAuthState, self._user_id.telegram_user_id)
                assert dbo
                dbo.state = self._state.value
                dbo.email = self._email
                dbo.code = self._code
                dbo.attempts = self._attempts
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


class TooManyAttemptsError(Exception):
    pass


class _Base(DeclarativeBase):
    pass


class _EmailAuthState(_Base):
    __tablename__ = "email_auth_states"

    telegram_user_id: Mapped[int] = mapped_column(primary_key=True)
    state: Mapped[int] = mapped_column(nullable=False)
    code: Mapped[Optional[str]] = mapped_column()
    email: Mapped[Optional[str]] = mapped_column()
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)


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
        self.assertIn(self.au._code, self.mm.sent[EmailAddress("john@example.net")][0])

        res = self.au.is_code_valid(self.au._code)
        self.assertTrue(res)

    def test_persistence(self):
        self.au.send_email("john@example.net")
        del self.au
        other = EmailAuthenticator(RepSysUserId(123), self.mm, self.eng)
        res = other.is_code_valid(other._code)
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
