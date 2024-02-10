from typing import Any, Optional
from dataclasses import dataclass
from bootshop.stories import (
    Controller,
)
from .session import Session


@dataclass
class ExchgController(Controller):
    _session: Session | None = None  # FIXME: this is ugly. Should be refactored

    @property
    def session(self) -> Session:
        # FIXME: this is ugly. Should be refactored
        if self._session is None:
            assert self.parent is not None
            assert isinstance(self.parent, ExchgController)
            return self.parent.session
        return self._session

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"
