from dataclasses import dataclass
from lib.exchange import Exchange


# FIXME: should go to the framework level
@dataclass
class Session:
    user_id: int
    user_name: str
    exchange: Exchange
