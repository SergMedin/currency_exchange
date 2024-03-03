from dataclasses import dataclass
from .rep_id import RepSysUserId


@dataclass
class AuthRecord:
    uid: RepSysUserId
    authenticated: bool
    when: float
