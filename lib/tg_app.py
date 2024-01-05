import asyncio
from decimal import Decimal, InvalidOperation
import os

from dotenv import load_dotenv
import datetime
from telegram import (
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from .db import Db
from .tg import Tg, TgMsg
from .exchange import Exchange
from .data import Match, Order, User, OrderType


class TgApp:
    # TODO:
    # - add lifetime to orders
    def __init__(self, db: Db, tg: Tg):
        self._db = db
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message
        self._ex = Exchange(self._db, self._on_match)

        load_dotenv()
        TG_TOKEN = os.getenv("TG_TOKEN")

        self.application = Application.builder().token(TG_TOKEN).build()
        self.application.add_handler(CommandHandler("start", self._start))
        self.application.add_handler(CommandHandler("add", self._add))
        self.application.add_handler(CommandHandler("list", self._list))
        self.application.add_handler(CommandHandler("remove", self._remove))
        # application.add_handler(create_order_handler)
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def _add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # await update.message.reply_text(f'Not implemented. Your message: {update.message.text}')
        chat_id = update.effective_chat.id
        message_text = update.message.text
        m = TgMsg(chat_id, message_text.split(" ", 1)[1])
        try:
            self._on_incoming_tg_message(m)
        except ValueError as e:
            await update.message.reply_text(
                f"The message has an incorrect format: {str(e)}"
            )

    async def _list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        def _convert_to_utc(creation_time, lifetime_sec):
            utc_date = datetime.datetime.utcfromtimestamp(creation_time + lifetime_sec)
            return utc_date

        orders = self._ex.list_orders_for_user(User(update.effective_chat.id))
        if len(orders) == 0:
            await update.message.reply_text("No orders")
        else:
            text = "Your orders:\n"
            for o in orders:
                utc_final_dttm = _convert_to_utc(o.creation_time, o.lifetime_sec)
                text += (
                    "\tid:\t"
                    + f"{o._id} ("
                    + f"{o.type.name} {o.amount_left} RUB * {o.price} AMD "
                    + f"min_amt {o.min_op_threshold} final_dttm {utc_final_dttm})\n"
                )
            await update.message.reply_text(text)
        # await update.message.reply_text('/list comand not implemented yet')

    async def _remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        remove_order_id = update.message.text.split(" ", 1)[1]
        try:
            self._ex.remove_order(int(remove_order_id))
            await update.message.reply_text(
                f"Order with id {remove_order_id} was removed"
            )
        except ValueError as e:
            await update.message.reply_text(
                f"The message has an incorrect format: {str(e)}"
            )

    def _on_incoming_tg_message(self, m: TgMsg):
        def _check_currencies(c1: str, c2: str) -> None:
            if c1 not in ["rub"] or c2 not in ["amd"]:
                raise ValueError("Invalid currency")

        def _check_price(price: str) -> None:
            try:
                price = Decimal(price)
                if price != price.quantize(Decimal("0.00")):
                    raise ValueError(
                        "Price has more than two digits after the decimal point"
                    )
            except InvalidOperation:
                raise ValueError("Invalid value for Decimal")

        def _check_amount(amount: Decimal) -> None:
            if amount <= 0:
                raise ValueError("Amount cannot be negative or zero")

        def _check_min_op_threshold(amount: Decimal, min_op_threshold: Decimal) -> None:
            if min_op_threshold < 0:
                raise ValueError("Minimum operational threshold cannot be negative")
            if min_op_threshold > amount:
                raise ValueError(
                    "Minimum operational threshold cannot be greater than the amount"
                )

        # ['buy', '1500', 'usd', '*', '98.1', 'rub', 'min_amt', '100']
        #  0      1       2      3    4       5      6          7
        pp = m.text.lower().strip().split(" ")
        print("INC TG MSG:", m, pp)
        _check_amount(Decimal(pp[1]))
        _check_min_op_threshold(Decimal(pp[1]), Decimal(pp[7]))
        _check_price(pp[4])
        _check_currencies(pp[2], pp[5])

        if pp[0] == "buy":
            ot = OrderType.BUY
        elif pp[0] == "sell":
            ot = OrderType.SELL
        else:
            raise ValueError("Invalid order type")

        amount = Decimal(pp[1])
        price = Decimal(pp[4])
        min_op_threshold = Decimal(pp[7])
        o = Order(User(m.user_id), ot, price, amount, min_op_threshold)
        self._ex.on_new_order(o)

    def _on_match(self, m: Match):
        buyer_id = m.buy_order.user.id
        seller_id = m.sell_order.user.id
        message_buyer = f"Go and buy {m.amount} from {seller_id} for {m.price} per unit"
        message_seller = (
            f"You should sell {m.amount} to {buyer_id} for {m.price} per unit"
        )
        # self._tg.send_message(TgMsg(buyer_id, message_buyer))
        # self._tg.send_message(TgMsg(seller_id, message_seller))
        asyncio.create_task(self.application.bot.send_message(buyer_id, message_buyer))
