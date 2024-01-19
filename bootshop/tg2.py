import asyncio
from lib.tg import Tg, TgIncomingMsg, TgOutgoingMsg

from telegram import Update, InlineKeyboardButton
from telegram.ext import Application, ContextTypes, MessageHandler, filters


class TgReal2(Tg):
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.application.add_handler(
            MessageHandler(filters.TEXT, self._default_handler)
        )

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

    def send_message(self, m: TgOutgoingMsg, parse_mode=None):
        asyncio.create_task(
            self.application.bot.send_message(m.user_id, m.text, parse_mode=parse_mode)
        )
