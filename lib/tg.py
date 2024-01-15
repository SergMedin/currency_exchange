from typing import Callable
from .data import TgMsg
import asyncio

from telegram import (
    Update,
)
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from telegram import InlineKeyboardButton, ReplyKeyboardMarkup

OnMessageType = Callable[[TgMsg], None]


class Tg:
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

    def send_message(self, m: TgMsg, parse_mode=None, reply_markup=None):
        if not isinstance(m, TgMsg):
            raise ValueError()
        self.outgoing.append(m)

    def emulate_incoming_message(self, from_user_id: int, from_user_name: str, text: str):
        m = TgMsg(from_user_id, from_user_name, text)
        self.incoming.append(m)
        if self.on_message:
            self.on_message(m)


class TelegramReal(Tg):
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.application.add_handler(MessageHandler(filters.TEXT, self._default_handler))

    def run_forever(self):
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def _default_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = TgMsg(
            update.effective_chat.id,
            update.effective_chat.username,
            update.message.text,
        )
        try:
            self.on_message(message)
        except ValueError as e:
            await update.message.reply_text(f"Error: {str(e)}")

    def send_message(self, m: TgMsg, parse_mode=None, reply_markup=None):
        if reply_markup:
            reply_markup = ReplyKeyboardMarkup(reply_markup, resize_keyboard=True, one_time_keyboard=True)
        # print("TG OUTGOING:", m)
        asyncio.create_task(
            self.application.bot.send_message(m.user_id, m.text, parse_mode=parse_mode, reply_markup=reply_markup)
        )
