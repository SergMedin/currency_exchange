import dataclasses
from typing import Callable


@dataclasses.dataclass
class TgMsg:
    user_id: int
    text: str


OnMessageType = Callable[[TgMsg], None]


class Tg:
    def __init__(self):
        self._on_message = None

    @property
    def on_message(self) -> OnMessageType:
        return self._on_message

    @on_message.setter
    def on_message(self, value: OnMessageType) -> None:
        self._on_message = value

    def send_message(self, m: TgMsg):
        raise NotImplementedError()


class TelegramMock(Tg):
    def __init__(self):
        super().__init__()
        self.outgoing: list[TgMsg] = []
        self.incoming: list[TgMsg] = []

    def send_message(self, m: TgMsg):
        # print("TG OUTGOING:", m)
        self.outgoing.append(m)

    def emulate_incoming_message(self, from_user_id: int, text: str):
        m = TgMsg(from_user_id, text)
        self.incoming.append(m)
        if self.on_message:
            try:
                self.on_message(m)
            except ValueError as e:
                self.send_message(TgMsg(from_user_id, f'The message has an incorrect format: {str(e)}'))
