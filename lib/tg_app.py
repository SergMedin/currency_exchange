from decimal import Decimal, InvalidOperation
import datetime

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

    def _on_incoming_tg_message(self, m: TgMsg):
        print("INC TG MSG:", m)

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

        pp = m.text.lower().strip().split(" ")
        command = pp[0]
        pp = pp[1:]
        if command == "/start":
            message = """
'Добро пожаловать в "обменник"!
Бот работает только с одной валютной парой: RUB/AMD. Можно создавать заявки на покупку или продажу. Примеры заявок ниже:
Продаю 1500 RUB по курсу 4.54 AMD за 1 RUB, минимальная сумма сделки 100 RUB, время жизни заявки 24 часа:
/add sell 1500 RUB * 4.54 AMD min_amt 100 lifetime_h 24

Куплю 1500 RUB по курсу 4.40 AMD за 1 RUB, минимальная сумма сделки 1500 RUB, время жизни заявки 48 часов:
/add buy 1500 RUB * 4.60 AMD min_amt 1500 lifetime_h 48


После создания заявки, она будет отображаться в списке заявок.
При совпадении заявок, они будут автоматически закрыты,
а пользователям, которые их оставили уйдут уведомления о необходимости совершить обмен.
Курс обмена будет рассчитан по формуле: (цена_продажи + цена_покупки) / 2

Посмотреть список заявок можно командой /list
Удалить заявку можно командой /remove <id заявки>

Время жизни заявки можно задать при её заведени, но она не может превышать 48 часов.
"""
            self._tg.send_message(TgMsg(m.user_id, m.user_name, message))
        elif command == "/add":
            try:
                # ['buy', '1500', 'usd', '*', '98.1', 'rub', 'min_amt', '100', 'lifetime_h', '48']
                #  0      1       2      3    4       5      6          7       8            9
                # pp = m.text.lower().strip().split(" ")
                # print("INC TG MSG:", m, pp)
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
                lifetime_h = int(pp[9])
                o = Order(
                    User(m.user_id, m.user_name),
                    ot,
                    price,
                    amount,
                    min_op_threshold,
                    lifetime_sec=lifetime_h * 3600,
                )
                self._ex.on_new_order(o)
            except ValueError as e:
                self._tg.send_message(
                    TgMsg(
                        m.user_id,
                        m.user_name,
                        f"The message has an incorrect format: {str(e)}",
                    )
                )
        elif command == "/list":

            def _convert_to_utc(creation_time, lifetime_sec):
                utc_date = datetime.datetime.utcfromtimestamp(
                    creation_time + lifetime_sec
                )
                return utc_date

            orders = self._ex.list_orders_for_user(User(m.user_id, m.user_name))
            if len(orders) == 0:
                self._tg.send_message(TgMsg(m.user_id, m.user_name, "No orders"))
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
                text += "\nto remove an order, use /remove <id>"
                self._tg.send_message(TgMsg(m.user_id, m.user_name, text))
                # self._tg.send_message(f"The message has an incorrect format: {str(e)}")
        # await update.message.reply_text('/list comand not implemented yet')
        elif command == "/remove":

            def _check_pp_for_remove(pp: list) -> None:
                if len(pp) == 1:
                    remove_order_id = pp[0]
                else:
                    raise ValueError(f"Invalid order id: {pp}")
                if not remove_order_id.isnumeric():
                    raise ValueError("Invalid order id")
                if int(remove_order_id) not in self._ex._orders:
                    raise ValueError("Order with this id does not exist")
                if self._ex._orders[int(remove_order_id)].user.id != m.user_id:
                    raise ValueError("This order belongs to another user")

            try:
                _check_pp_for_remove(pp)
                remove_order_id = pp[0]
                self._ex.remove_order(int(remove_order_id))
                self._tg.send_message(
                    TgMsg(
                        m.user_id,
                        m.user_name,
                        f"Order with id {remove_order_id} was removed",
                    )
                )
                print(
                    f"Order with id {remove_order_id} was removed and message was sent"
                )
            except ValueError as e:
                self._tg.send_message(
                    TgMsg(
                        m.user_id,
                        m.user_name,
                        f"The message has an incorrect format: {str(e)}",
                    )
                )
        else:
            raise ValueError("Invalid command")
        return

    def _on_match(self, m: Match):
        buyer_id = m.buy_order.user.id
        buyer_name = m.buy_order.user.name
        seller_id = m.sell_order.user.id
        seller_name = m.sell_order.user.name
        message_buyer = (
            f"Go and buy {m.amount} from @{seller_name} for {m.price} per unit (you should send"
            f" {m.price * m.amount:.2f} AMD, you will get {m.amount:.2f} RUB)"
        )
        message_seller = (
            f"You should sell {m.amount} to @{buyer_name} for {m.price} per unit (you should send"
            f" {m.amount:.2f} RUB, you will get {m.price * m.amount:.2f} AMD)"
        )
        self._tg.send_message(TgMsg(buyer_id, buyer_name, message_buyer))
        self._tg.send_message(TgMsg(seller_id, seller_name, message_seller))
