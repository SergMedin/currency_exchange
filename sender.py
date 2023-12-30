import asyncio
from telegram import ext
import config_example
import os


def find_chat_id_by_username(username):
    """ Находит chat_id по username в файле user_ids.txt. """
    try:
        with open(filename, 'r') as file:
            for line in file:
                user_name, chat_id = line.strip().split(':')
                if user_name == username:
                    return chat_id
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
        return None


async def send_message_to_user(username, message):
    """ Отправляет сообщение пользователю по его username. """
    chat_id = find_chat_id_by_username(username)
    if chat_id:
        try:
            await application.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")
    else:
        print(f"Пользователь {username} не найден.")


async def send_initial_messages():
    await send_message_to_user('serg_medin', 'Привет')


async def run_bot():
    # Создаем асинхронную задачу для отправки сообщений
    await send_initial_messages()

    # Запускаем бота
    await application.run_polling()


def main():
    global application, filename
    bot_token = os.environ.get("TG_BOT_TOKEN", config_example.bot_token)
    application = ext.Application.builder().token(bot_token).build()

    filename = 'user_ids.txt'

    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
