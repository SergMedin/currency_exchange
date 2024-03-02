from dataclasses import dataclass
from typing import Optional
from hashlib import sha256


@dataclass
class RepSysUserId:
    telegram_user_id: Optional[int] = None
    email_hash: Optional[str] = None

    @classmethod
    def hash_email(cls, email: str) -> str:
        return sha256((email + EMAIL_SALT).encode()).hexdigest()

    @classmethod
    def from_email(cls, email: str) -> "RepSysUserId":
        return cls(email_hash=cls.hash_email(email))


EMAIL_SALT = "oETx$&xScuwcsmVh"
