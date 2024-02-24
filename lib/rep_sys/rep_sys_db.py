import time
from unittest import TestCase
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session
from .auth_rec import AuthRecord


class RepSysDb:
    def __init__(self, eng):
        assert isinstance(eng, Engine)
        self._eng = eng
        _Base.metadata.create_all(self._eng)

    def get_auth_record(self, tg_user_id: int) -> "AuthRecord":
        with Session(self._eng) as session:
            dbo = session.get(_Auths, tg_user_id)
            if dbo is None:
                raise KeyError()
            return AuthRecord(dbo.authenticated, dbo.when)

    def set_authenticity(self, tg_user_id: int, is_auth: bool) -> None:
        t = int(time.time())
        with Session(self._eng) as session:
            dbo = session.get(_Auths, tg_user_id)
            if dbo is None:
                dbo = _Auths(telegram_user_id=tg_user_id, authenticated=is_auth, when=t)
                session.add(dbo)
            else:
                dbo.authenticated = is_auth
                dbo.when = t
            session.commit()


class _Base(DeclarativeBase):
    pass


class _Auths(_Base):
    __tablename__ = "auths"
    telegram_user_id: Mapped[int] = mapped_column(primary_key=True)
    authenticated: Mapped[bool] = mapped_column()
    when: Mapped[int] = mapped_column()


class T(TestCase):

    def test_empty(self):
        eng = create_engine("sqlite://")
        rs = RepSysDb(eng)
        self.assertRaises(KeyError, rs.get_auth_record, 123)

    def test_set(self):
        eng = create_engine("sqlite://")
        rs = RepSysDb(eng)
        rs.set_authenticity(123, True)
        self.assertTrue(rs.get_auth_record(123).authenticated)
        rs.set_authenticity(123, False)
        self.assertFalse(rs.get_auth_record(123).authenticated)
