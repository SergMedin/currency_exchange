import os

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    filters,
    MessageHandler,
)

# from data import Order
# from db_handler import BOT_DB


# def pairwise(iterable, n=2):
#     return zip(*[iter(iterable)] * n)


# async def wake_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     buttons = ReplyKeyboardMarkup(
#         [["Создать заявку", "Мои заявки"], ["Статистика", "История заявок"]],
#         resize_keyboard=True,
#         one_time_keyboard=True,
#     )
#     first_name = update.effective_chat.first_name
#     uname = update.effective_chat.username
#     uid = update.effective_chat.id
#     # participant = Participant(update, context, db) # is it really need? Need atomarity
#     db.create_or_update_user(tg_username=uname, tg_id=uid)

#     await update.message.reply_text(
#         f"Привет, {first_name}!\n" 'Добро пожаловать в "обменник"!',
#         reply_markup=buttons,
#     )
#     await context.bot.send_message(  # message to the bot owner, remove before launch
#         chat_id=os.getenv("O_CHAT_ID"),
#         text=f"{first_name}, username {uname} with uid {uid} just have used our bot!",
#     )


# async def create_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     uid = update.effective_chat.id
#     unfinished_orders[uid] = Order(uid)
#     twinned_pairs = pairwise(db.get_currency_pairs())
#     buttons = []
#     for twin_pair in twinned_pairs:
#         buttons.append(
#             [
#                 InlineKeyboardButton(
#                     twin_pair[0][1], callback_data=twin_pair[0][0]
#                 ),  # transfer more data
#                 InlineKeyboardButton(twin_pair[1][1], callback_data=twin_pair[1][0]),
#             ]
#         )
#     reply_markup = InlineKeyboardMarkup(buttons)

#     await update.message.reply_text(
#         "Выберите валютную пару", reply_markup=reply_markup
#     )  # ?


# async def order_currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer(f"Selected: {query.data}")
#     unfinished_orders[update.effective_chat.id].currency_pair = query.data
#     await query.edit_message_text("Укажите сумму для обмена")
#     return AMOUNT


# async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     unfinished_orders[update.effective_chat.id].amount = update.message.text
#     await update.message.reply_text("Напишите желаемый курс обмена")
#     return WISHED_PRICE


# async def get_wished_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     unfinished_orders[update.effective_chat.id].wished_price = update.message.text
#     await update.message.reply_text("Укажите минимальный объем для обмена")
#     return MINIMAL_TRANSACTION


# async def get_minimal_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     unfinished_orders[
#         update.effective_chat.id
#     ].minimal_transaction = update.message.text
#     await update.message.reply_text(
#         "Укажите время существования заявки в часах. "
#         "Максимально - 48 часов, по-умолчанию - 48 часов"
#     )
#     return DURATION


# async def get_order_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     unfinished_orders[update.effective_chat.id].duration = update.message.text
#     order_text = unfinished_orders[update.effective_chat.id].__str__()
#     buttons = ReplyKeyboardMarkup(
#         [["Подтвердить", "Отменить"]], resize_keyboard=True, one_time_keyboard=True
#     )
#     await update.message.reply_text(
#         f"Подтвердите заявку: {order_text}", reply_markup=buttons
#     )
#     return CONFIRMATION


# async def order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     decision = update.message.text
#     if decision == "Подтвердить":
#         unfinished_orders[update.effective_chat.id].set_time()
#         db.create_order(unfinished_orders[update.effective_chat.id])
#         del unfinished_orders[update.effective_chat.id]
#         await update.message.reply_text("Заказ успешно создан!")
#     elif decision == "Отменить":
#         del unfinished_orders[update.effective_chat.id]
#         await update.message.reply_text("Создание заказа было отменено")
#     else:  # inappropriate
#         await update.message.reply_text("Неизвестная команда")
#     await wake_up(update, context)


# async def order_creation_failure(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text("Что-то пошло не так")


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first_name = update.effective_chat.first_name
    # uname = update.effective_chat.username
    # uid = update.effective_chat.id

    await update.message.reply_text(
        f"""
Привет, {first_name}!
'Добро пожаловать в "обменник"!
Бот работает только с одной валютной парой: RUB/AMD. Можно создавать заявки на покупку или продажу. Примеры заявок:
/add buy 1500 RUB * 98.1 AMD min_amt 100
/add sell 1500 RUB * 98.1 AMD min_amt 100


После создания заявки, она будет отображаться в списке заявок. При совпадении заявок, они будут автоматически закрыты, а пользователям, которые их оставили уйдут уведомления о необходимости совершить обмен.
Курс обмена будет рассчитан по формуле: (цена_продажи + цена_покупки) / 2

Посмотреть список заявок можно командой /list
Удалить заявку можно командой /remove <id заявки>

Время жизни заявки можно задать при её заведени, но она не может превышать 48 часов.
""",
    )


async def _add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # await update.message.reply_text('/add comand not implemented yet')
    await update.message.reply_text(f'Not implemented. Your message: {update.message.text}')


async def _list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('/list comand not implemented yet')


async def _remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('/remove comand not implemented yet')


def main():
    load_dotenv()
    TG_TOKEN = os.getenv("TG_TOKEN")

    application = Application.builder().token(TG_TOKEN).build()
    application.add_handler(CommandHandler("start", _start))
    application.add_handler(CommandHandler("add", _add))
    application.add_handler(CommandHandler("list", _list))
    application.add_handler(CommandHandler("remove", _remove))
    # application.add_handler(create_order_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()