from telegram import Update, ext
import schedule
import threading
import time
from config import bot_token

# Создаем экземпляр Application
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
