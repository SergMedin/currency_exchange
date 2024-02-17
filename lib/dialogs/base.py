from typing import Any, Optional
from dataclasses import dataclass
from ..botlib.stories import Controller, OutMessage, ButtonAction
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

    def edit_last(self, btn_event: ButtonAction, msg: OutMessage) -> "OutMessage":
        if btn_event.message_id is not None:
            btn = self.get_button_by_action(btn_event.name)
            if btn:
                msg = (
                    OutMessage(
                        text=f"*— {btn.text}*",
                        edit_message_with_id=btn_event.message_id,
                    )
                    + msg
                )
        return msg
