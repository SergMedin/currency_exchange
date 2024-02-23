from dataclasses import dataclass
from typing import Optional
from lib.exchange import Exchange
from lib.rep_sys import ReputationSystem
from lib.rep_sys.email_auth import EmailAuthenticator


# FIXME: should go to the framework level
@dataclass
class Session:
    user_id: int
    user_name: str
    exchange: Exchange
    rep_sys: ReputationSystem
    email_auth: Optional[EmailAuthenticator] = None
