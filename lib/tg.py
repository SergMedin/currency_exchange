from typing import Callable, Optional
import asyncio
import dataclasses
import logging
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
import telegram


@dataclasses.dataclass
class TgIncomingMsg:
    user_id: int
    user_name: str
    text: str
    keyboard_callback: str | None = None


@dataclasses.dataclass
class InlineKeyboardButton:
    text: str
    callback_data: str


@dataclasses.dataclass
class TgOutgoingMsg:
    user_id: int
    user_name: str | None
    text: str
    inline_keyboard: list[list[InlineKeyboardButton]] | None = None
    reply_markup: Optional[str] = None
    parse_mode: Optional[str] = None


OnMessageType = Callable[[TgIncomingMsg], None]


class Tg:
    @property
    def on_message(self) -> OnMessageType:
        return self._on_message

    @on_message.setter
    def on_message(self, value: OnMessageType) -> None:
        self._on_message = value

    def send_message(
        self, m: TgOutgoingMsg, parse_mode=None, reply_markup=None
    ):  # FIXME: should be removed: , parse_mode=None, reply_markup=None
        raise NotImplementedError()


class TelegramMock(Tg):
    def __init__(self):
        super().__init__()
        self.outgoing: list[TgOutgoingMsg] = []  # type: ignore
        self.incoming: list[TgIncomingMsg] = []  # type: ignore

    def send_message(self, m: TgOutgoingMsg, parse_mode=None, reply_markup=None):
        if not isinstance(m, TgOutgoingMsg):
            raise ValueError()
        self.outgoing.append(m)

    def emulate_incoming_message(
        self, from_user_id: int, from_user_name: str, text: str
    ):
        m = TgIncomingMsg(from_user_id, from_user_name, text)
        self.incoming.append(m)
        if self.on_message is not None:
            self.on_message(m)


class TelegramReal(Tg):
    def __init__(self, token: str):
        # print(f"token: ...{token[-5:]}")
        self.application: Application = Application.builder().token(token).build()
        self.application.add_handler(
            MessageHandler(filters.TEXT, self._default_handler)
        )
        self.application.add_handler(CallbackQueryHandler(self._callback_query_handler))

    def run_forever(self):
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def _default_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        if (
            update.effective_chat is None
            or update.effective_chat.username is None
            or update.message is None
            or update.message.text is None
        ):
            logging.warning(f"got invalid message. Update: {update}")
            return
        message = TgIncomingMsg(
            update.effective_chat.id,
            update.effective_chat.username,
            update.message.text,
        )
        try:
            self.on_message(message)
        except ValueError as e:
            await update.message.reply_text(f"Error: {str(e)}")

    async def _callback_query_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        # logging.info(f"got callback query. Update: {update}")
        query = update.callback_query
        if query is None:
            logging.warning(f"got invalid callback query. Update: {update}")
            return
        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        await query.answer()
        # await query.edit_message_text(text=f"Selected option: {query.data}")

        if update.effective_chat is None or update.effective_chat.username is None:
            logging.warning(f"got invalid query callback update. Update: {update}")
            return
        message = TgIncomingMsg(
            update.effective_chat.id,
            update.effective_chat.username,
            "",
            keyboard_callback=query.data,
        )
        try:
            self.on_message(message)
        except ValueError as e:
            logging.error(f"Error: {str(e)}")
            # await update.message.reply_text(f"Error: {str(e)}")

    def send_message(self, m: TgOutgoingMsg, parse_mode=None, reply_markup=None):
        if reply_markup:
            reply_markup = telegram.ReplyKeyboardMarkup(
                reply_markup, resize_keyboard=True, one_time_keyboard=True
            )
        if m.inline_keyboard:
            keyboard = [
                [
                    telegram.InlineKeyboardButton(
                        button.text, callback_data=button.callback_data
                    )
                    for button in row
                ]
                for row in m.inline_keyboard
            ]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        asyncio.create_task(
            self.application.bot.send_message(
                m.user_id, m.text, parse_mode=parse_mode, reply_markup=reply_markup
            )
        )
