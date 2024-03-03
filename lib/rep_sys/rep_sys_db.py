import time
from unittest import TestCase
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session
from .auth_rec import AuthRecord
from .rep_id import RepSysUserId


class RepSysDb:
    def __init__(self, eng):
        assert isinstance(eng, Engine)
        self._eng = eng
        _Base.metadata.create_all(self._eng)

    def get_auth_record(self, uid: RepSysUserId) -> "AuthRecord":
        with Session(self._eng) as session:
            if uid.telegram_user_id is not None:
                dbo = (
                    session.query(_Auths)
                    .filter(_Auths.telegram_user_id == uid.telegram_user_id)
                    .one_or_none()
                )
            elif uid.email_hash is not None:
                dbo = (
                    session.query(_Auths)
                    .filter(_Auths.email_hash == uid.email_hash)
                    .one_or_none()
                )
            else:
                raise ValueError("Either telegram_user_id or email_hash must be set")

            if dbo is None:
                raise KeyError()
            uid = RepSysUserId(dbo.telegram_user_id, dbo.email_hash)
            return AuthRecord(uid, dbo.authenticated, dbo.when)

    def set_authenticity(self, uid: RepSysUserId, is_auth: bool) -> None:
        assert uid.telegram_user_id
        t = int(time.time())
        with Session(self._eng) as session:
            dbo = session.get(_Auths, uid.telegram_user_id)
            if dbo is None:
                dbo = _Auths(
                    telegram_user_id=uid.telegram_user_id,
                    email_hash=uid.email_hash,
                    authenticated=is_auth,
                    when=t,
                )
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
    email_hash: Mapped[str] = mapped_column(unique=True, nullable=True)
    authenticated: Mapped[bool] = mapped_column()
    when: Mapped[int] = mapped_column()


class T(TestCase):

    def test_empty(self):
        eng = create_engine("sqlite://")
        rs = RepSysDb(eng)
        self.assertRaises(KeyError, rs.get_auth_record, RepSysUserId(123))

    def test_set(self):
        eng = create_engine("sqlite://")
        rs = RepSysDb(eng)
        rs.set_authenticity(RepSysUserId(123), True)
        self.assertTrue(rs.get_auth_record(RepSysUserId(123)).authenticated)
        rs.set_authenticity(RepSysUserId(123), False)
        self.assertFalse(rs.get_auth_record(RepSysUserId(123)).authenticated)
