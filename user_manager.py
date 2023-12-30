from telegram import Update, ext
import threading
import time
import os
import config_example


def main():
    # Создаем экземпляр Application
    bot_token = os.environ.get("TG_BOT_TOKEN", config_example.bot_token)
    application = ext.Application.builder().token(bot_token).build()

    # Файл для хранения связки username и user_id
    filename = 'user_ids.txt'

    def save_user(chat_id, username):
        with open(filename, 'a+') as file:
            file.seek(0)
            if any(username in line for line in file):
                return  # Пользователь уже сохранен
            file.write(f"{username}:{chat_id}\n")

    async def start(update: Update, context: ext.CallbackContext):
        chat_id = update.effective_chat.id
        username = update.message.chat.username
        save_user(chat_id, username)
        # await context.bot.send_message(chat_id=chat_id, text="Привет! Вы подписались на напоминания.")

    # Добавление обработчика команды /start
    start_handler = ext.CommandHandler('start', start)
    application.add_handler(start_handler)

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    main()
