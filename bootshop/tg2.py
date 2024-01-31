import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from lib.tg import Tg, TgIncomingMsg, TgOutgoingMsg


class TgReal2(Tg):
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.application.add_handler(
            MessageHandler(filters.TEXT, self._default_handler),
        )
        self.application.add_handler(CallbackQueryHandler(self._callback_query_handler))

    def run_forever(self):
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def _default_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
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
        logging.info(f"got callback query. Update: {update}")
        query = update.callback_query
        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        await query.answer()
        await query.edit_message_text(text=f"Selected option: {query.data}")

    def send_message(self, m: TgOutgoingMsg, parse_mode=None):
        keyboard = [
            [
                InlineKeyboardButton("Option 1", callback_data="1"),
                InlineKeyboardButton("Option 2", callback_data="2"),
            ],
            [InlineKeyboardButton("Option 3", callback_data="3")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        asyncio.create_task(
            self.application.bot.send_message(
                m.user_id, m.text, parse_mode=parse_mode, reply_markup=reply_markup
            )
        )
