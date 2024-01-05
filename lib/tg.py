from typing import Callable
from .data import TgMsg
import asyncio

import os

from dotenv import load_dotenv

from telegram import (
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

OnMessageType = Callable[[TgMsg], None]


class Tg:
    def __init__(self):
        # self._on_message = None
        pass

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
        if not isinstance(m, TgMsg):
            raise ValueError("SSSSSS")
        self.outgoing.append(m)

    def emulate_incoming_message(
        self, from_user_id: int, from_user_name: str, text: str
    ):
        m = TgMsg(from_user_id, from_user_name, text)
        self.incoming.append(m)
        if self.on_message:
            self.on_message(m)
            # try:
            #     self.on_message(m)
            # except ValueError as e:
            #     self.send_message(
            #         TgMsg(
            #             from_user_id,
            #             from_user_name,
            #             f"The message has an incorrect format: {str(e)}",
            #         )
            #     )


class TelegramReal(Tg):
    def __init__(self):
        load_dotenv()
        TG_TOKEN = os.getenv("TG_TOKEN")

        # TODO:
        #  - remove CommandHandler / use one Handler for all commands
        self.application = Application.builder().token(TG_TOKEN).build()
        self.application.add_handler(CommandHandler("start", self._default_handler))
        self.application.add_handler(CommandHandler("add", self._default_handler))
        self.application.add_handler(CommandHandler("list", self._default_handler))
        self.application.add_handler(CommandHandler("remove", self._default_handler))

    def run_forever(self):
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def _default_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        message = TgMsg(
            update.effective_chat.id,
            update.effective_chat.username,
            update.message.text,
        )
        self.on_message(message)

    def send_message(self, m: TgMsg):
        # print("TG OUTGOING:", m)
        asyncio.create_task(self.application.bot.send_message(m.user_id, m.text))
