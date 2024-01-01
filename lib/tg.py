import dataclasses


@dataclasses.dataclass
class TgMsg:
    user_id: int
    text: str


class Tg:
    def on_message(self, m: TgMsg):
        raise NotImplementedError()

    def send_message(self, m: TgMsg):
        raise NotImplementedError()


class TelegramMock(Tg):
    def __init__(self):
        self.outgoing: list[TgMsg] = []
        self.incoming: list[TgMsg] = []

    def send_message(self, m: TgMsg):
        # print("TG OUTGOING:", m)
        self.outgoing.append(m)

    def add_message(self, from_user_id: int, text: str):
        m = TgMsg(from_user_id, text)
        self.incoming.append(m)
        try:
            self.on_message(m)
        except ValueError as e:
            self.send_message(TgMsg(from_user_id, f'The message has an incorrect format: {str(e)}'))
