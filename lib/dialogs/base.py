from typing import Any, Optional
from dataclasses import dataclass
from bootshop.stories import Controller, OutMessage
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

    def edit_last(self, btn_action_name: str | None, msg: OutMessage) -> "OutMessage":
        btn = self.get_button_by_action(btn_action_name) if btn_action_name else None
        if btn:
            msg = msg + OutMessage(
                text=f"*— {btn.text}*", edit_the_last=True, parse_mode="Markdown"
            )
        return msg
