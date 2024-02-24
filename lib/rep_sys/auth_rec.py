from dataclasses import dataclass


@dataclass
class AuthRecord:
    authenticated: bool
    when: float
