from decimal import Decimal, InvalidOperation
import datetime

from .db import Db
from .tg import Tg, TgMsg
from .exchange import Exchange
from .data import Match, Order, User, OrderType
from .logger import get_logger


logger = get_logger(__name__)

with open("./lib/tg_messages/start_message.md", "r") as f:
    tg_start_message = f.read().strip()


class Validator:
    def validate_add_command_params(self, params):
        if len(params) != 10:
            raise ValueError("Invalid number of arguments")
        if params[0] not in ["buy", "sell"]:
            raise ValueError(f"Invalid order type: {params[0]}")
        if not params[1].isnumeric():
            raise ValueError(f"Invalid amount: {params[1]}")
        if params[2] not in ["rub"]:
            raise ValueError(f"Invalid currency: {params[2]}")
        if params[3] != "*":
            raise ValueError(f"Invalid separator: {params[3]}")
        # it will be checked below
        # if not params[4].isnumeric():
        #     raise ValueError(f"Invalid price: {params[4]}")
        if params[5] not in ["amd"]:
            raise ValueError(f"Invalid currency: {params[5]}")
        if params[6] != "min_amt":
            raise ValueError(f"Invalid separator: {params[6]}")
        if not params[7].isnumeric():
            raise ValueError(f"Minimum operational threshold cannot be negative: {params[7]}")
        if params[8] != "lifetime_h":
            raise ValueError(f"Invalid separator: {params[8]}")
        if not params[9].isnumeric():
            raise ValueError(f"Invalid lifetime: {params[9]}")

        try:
            price = Decimal(params[4])
            if price != price.quantize(Decimal("0.00")):
                raise ValueError(
                    f"Price has more than two digits after the decimal point: {params[4]}"
                )
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {params[4]}")

        try:
            amount = Decimal(params[1])
            if amount <= 0:
                raise ValueError("Amount cannot be negative or zero")
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {params[1]}")

        try:
            min_op_threshold = Decimal(params[7])
            if min_op_threshold < 0:
                raise ValueError("Minimum operational threshold cannot be negative")
            if min_op_threshold > amount:
                raise ValueError(
                    "Minimum operational threshold cannot be greater than the amount"
                )
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {params[7]}")

    def validate_remove_command_params(self, params, exchange, user_id):
        if len(params) == 1:
            remove_order_id = params[0]
        else:
            raise ValueError(f"Invalid remove params: {params}")
        if not remove_order_id.isnumeric():
            raise ValueError(f"Invalid order id: {remove_order_id}")
        if int(remove_order_id) not in exchange._orders:
            raise ValueError(f"Invalid order id: {remove_order_id}")
        if exchange._orders[int(remove_order_id)].user.id != user_id:
            # User should not be able realize that order with this id exists
            raise ValueError(f"Invalid order id: {remove_order_id}")


class TgApp:
    # TODO:
    # - add lifetime to orders
    def __init__(self, db: Db, tg: Tg):
        self._db = db
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message
        self._ex = Exchange(self._db, self._on_match)
        self._validator = Validator()

    def _send_message(self, user_id, user_name, message, parse_mode=None):
        self._tg.send_message(TgMsg(user_id, user_name, message), parse_mode=parse_mode)

    def _on_incoming_tg_message(self, m: TgMsg):
        try:
            if m.user_id < 0:
                raise ValueError("We don't work with groups yet")

            pp = m.text.lower().strip().split(" ")
            command = pp[0]
            params = pp[1:]

            if command == '/start':
                self._send_message(m.user_id, m.user_name, tg_start_message, parse_mode='Markdown')
            elif command == '/add':
                self._handle_add_command(m, params)
            elif command == '/list':
                self._handle_list_command(m)
            elif command == '/remove':
                self._handle_remove_command(m, params)
            elif command == '/stat':
                self._handle_stat_command(m)
            else:
                raise ValueError(f"Invalid command: {command}")

        except ValueError as e:
            self._send_message(m.user_id, m.user_name, f"Error: {str(e)}")

    def _handle_stat_command(self, m: TgMsg):
        text = self._ex.get_stats()['text']
        self._send_message(m.user_id, m.user_name, text)

    def _handle_add_command(self, m: TgMsg, params: list):
        self._validator.validate_add_command_params(params)
        order_type = OrderType[params[0].upper()]
        amount = Decimal(params[1])
        price = Decimal(params[4])
        min_op_threshold = Decimal(params[7])
        lifetime_h = int(params[9])

        o = Order(
            User(m.user_id, m.user_name),
            order_type,
            price,
            amount,
            min_op_threshold,
            lifetime_sec=lifetime_h * 3600,
        )
        self._send_message(m.user_id, m.user_name, "We get your order")
        self._ex.on_new_order(o)

    def _handle_list_command(self, m: TgMsg):
        orders = self._ex.list_orders_for_user(User(m.user_id, m.user_name))
        if not orders:
            self._send_message(m.user_id, m.user_name, "No orders")
        else:
            text = "Your orders:\n" + "\n".join(
                [
                    f"\tid: {o._id} ({o.type.name} {o.amount_left} RUB * {o.price} AMD "
                    f"min_amt {o.min_op_threshold} lifetime_h {int(o.lifetime_sec/3600)} "
                    f"[until: {self._convert_to_utc(o.creation_time, o.lifetime_sec)}])"
                    for o in orders
                ]
            ) + "\n\nto remove an order, use /remove <id>"
            self._send_message(m.user_id, m.user_name, text)

    def _handle_remove_command(self, m: TgMsg, params: list):
        self._validator.validate_remove_command_params(params, self._ex, m.user_id)
        remove_order_id = int(params[0])
        self._ex.remove_order(remove_order_id)
        self._send_message(m.user_id, m.user_name, f"Order with id {remove_order_id} was removed")

    @staticmethod
    def _convert_to_utc(creation_time, lifetime_sec):
        return datetime.datetime.utcfromtimestamp(creation_time + lifetime_sec)

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
