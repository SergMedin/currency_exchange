from decimal import Decimal, InvalidOperation
import datetime
import os

from tinydb import TinyDB, Query

from .db import Db
from .tg import Tg, TgMsg
from .exchange import Exchange
from .gsheets_loger import GSheetsLoger
from .data import Match, Order, User, OrderType
from .logger import get_logger
from .statemachines import OrderCreation


logger = get_logger(__name__)


class Validator:
    def validate_add_command_params(self, params):
        if len(params) != 10:
            raise ValueError("Invalid number of arguments")
        self.validate_order_type(params[0])
        self.validate_amount(params[1])
        self.validate_currency_from(params[2])
        if params[3] != "*":
            raise ValueError(f"Invalid separator: {params[3]}")
        self.validate_price(params[4])
        self.validate_currency_to(params[5])
        if params[6] != "min_amt":
            raise ValueError(f"Invalid separator: {params[6]}")
        self.validate_min_op_threshold(params[7], params[1])
        if params[8] != "lifetime_h":
            raise ValueError(f"Invalid separator: {params[8]}")
        self.validate_lifetime(params[9])

    def validate_order_type(self, order_type: str):
        if order_type.capitalize() not in ["Buy", "Sell"]:
            raise ValueError(f"Invalid order type: {order_type}")

    def validate_amount(self, amount: str):
        if not amount.isnumeric():
            raise ValueError(f"Invalid amount: {amount}")
        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount cannot be negative or zero")
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {amount}")

    def validate_currency_from(self, currency_from: str):
        if currency_from.lower() not in ["rub"]:
            raise ValueError(f"Invalid currency: {currency_from}")

    def validate_currency_to(self, currency_to: str):
        if currency_to.lower() not in ["amd"]:
            raise ValueError(f"Invalid currency: {currency_to}")

    def validate_price(self, price: str):
        try:
            price = Decimal(price)
            if price != price.quantize(Decimal("0.00")):
                raise ValueError(f"Price has more than two digits after the decimal point: {price}")
            elif price <= 0:
                raise ValueError("Price cannot be negative or zero")
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {price}")

    def validate_min_op_threshold(self, min_op_threshold: str, amount: str):
        try:
            min_op_threshold = Decimal(min_op_threshold)
            amount = Decimal(amount)
            if min_op_threshold < 0:
                raise ValueError("Minimum operational threshold cannot be negative")
            if min_op_threshold > amount:
                raise ValueError("Minimum operational threshold cannot be greater than the amount")
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {min_op_threshold}")

    def validate_lifetime(self, lifetime: str):
        if not lifetime.isnumeric():
            raise ValueError(f"Invalid lifetime: {lifetime}")
        if int(lifetime) < 0:
            raise ValueError(f"Lifetime cannot be negative")
        if int(lifetime) > 48:
            raise ValueError(f"Lifetime cannot be greater than 48 hours")

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


class Application:
    MAIN_MENU_BUTTONS = [["Создать заявку", "Мои заявки"], ["Статистика", "Помощь"]]  # TODO: 'История заявок'

    def __init__(self, db: Db, tg: Tg, zmq_orders_log_endpoint=None, log_spreadsheet_key=None):
        self._db = db
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message
        self._ex = Exchange(self._db, self._on_match, zmq_orders_log_endpoint)
        self._sessions = {}
        self._app_db = TinyDB("app_db.json")
        if zmq_orders_log_endpoint:
            assert log_spreadsheet_key is not None
            worksheet_title = os.getenv("GOOGLE_SPREADSHEET_SHEET_TITLE", None)
            self._loger = GSheetsLoger(zmq_orders_log_endpoint, log_spreadsheet_key, worksheet_title)
            self._loger.start()
        self._validator = Validator()

    def shutdown(self):
        self._loger.stop()

    def _send_message(self, user_id, user_name, message, parse_mode=None, reply_markup=None):
        self._tg.send_message(TgMsg(user_id, user_name, message), parse_mode=parse_mode, reply_markup=reply_markup)

    def _check_unfinished_session(self, m: TgMsg):
        user_query = self._app_db.search(Query().user_id == m.user_id)
        if user_query:
            if user_query[0].get("order_creation_state_machine"):
                return user_query[0]

    def _on_incoming_tg_message(self, m: TgMsg):
        try:
            if m.user_id < 0:
                raise ValueError("We don't work with groups yet")

            if m.text == "Создать заявку":
                self._prepare_order_creation(m)

            if self._sessions.get(m.user_id):
                if self._sessions[m.user_id].get("order_creation_state_machine"):
                    self._handle_order_creation_sm(m)
                    return
                else:
                    session = self._check_unfinished_session(m)
                    if session:
                        self._prepare_order_creation(m, session)
                        self._handle_order_creation_sm(m)
                        return
            else:
                session = self._check_unfinished_session(m)
                if session:
                    self._prepare_order_creation(m, session)
                    self._handle_order_creation_sm(m)
                    return

            pp = m.text.lower().strip().split(" ")
            command = pp[0]
            params = pp[1:]

            if command == "/start":
                with open("./lib/tg_messages/start_message.md", "r") as f:
                    tg_start_message = f.read().strip()
                self._send_message(
                    m.user_id, m.user_name, tg_start_message, parse_mode="Markdown", reply_markup=self.MAIN_MENU_BUTTONS
                )
            elif command == "/help" or m.text == "Помощь":
                with open("./lib/tg_messages/help_message.md", "r") as f:
                    tg_help_message = f.read().strip()
                self._send_message(
                    m.user_id, m.user_name, tg_help_message, parse_mode="Markdown", reply_markup=self.MAIN_MENU_BUTTONS
                )
            elif command == "/add":
                self._handle_add_command(m, params)
            elif command == "/list" or m.text == "Мои заявки":
                self._handle_list_command(m)
            elif command == "/remove":
                self._handle_remove_command(m, params)
            elif command == "/stat" or m.text == "Статистика":
                self._handle_stat_command(m)
            else:
                raise ValueError(f"Invalid command: {command}")

        except ValueError as e:
            self._send_message(m.user_id, m.user_name, f"Error: {str(e)}")

    def _handle_stat_command(self, m: TgMsg):
        self._ex._check_order_lifetime()
        text = self._ex.get_stats()["text"]
        self._send_message(m.user_id, m.user_name, text, reply_markup=self.MAIN_MENU_BUTTONS)

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
        self._send_message(m.user_id, m.user_name, "We get your order", reply_markup=self.MAIN_MENU_BUTTONS)
        self._ex.on_new_order(o)

    def _prepare_order_creation(self, m: TgMsg, session=None):
        self._sessions[m.user_id] = {
            "order_creation_state_machine": OrderCreation(m.user_id),
            "order": Order(User(m.user_id, m.user_name), None, None, None, None, None),
        }
        if session:
            self._sessions[m.user_id]["order_creation_state_machine"].state = session["order_creation_state_machine"]
            for key, value in session["order"].items():
                if key == "user_id" or key == "user_name":
                    continue
                elif key == "type":
                    self._sessions[m.user_id]["order"].type = OrderType[value]
                elif key in ["amount_initial", "amount_left", "price", "min_op_threshold"]:
                    self._sessions[m.user_id]["order"].__setattr__(key, Decimal(value))
                else:
                    self._sessions[m.user_id]["order"].__setattr__(key, value)
        else:
            self._app_db.insert({"user_id": m.user_id, "user_name": m.user_name})
            self._app_db.update({"order_creation_state_machine": "start"}, Query().user_id == m.user_id)
            self._app_db.update({"order": "start"}, Query().user_id == m.user_id)

    def _handle_order_creation_sm(self, m: TgMsg):
        state = self._sessions[m.user_id]["order_creation_state_machine"].state
        if state == "start":
            text = "Выберите тип заявки"
            reply_markup = [["Купить", "Продать"]]
            self._sessions[m.user_id]["order_creation_state_machine"].new_order()
            self._app_db.update(
                {"order": {"user_id": m.user_id, "user_name": m.user_name}},
                Query().user_id == m.user_id,
            )
            self._app_db.update({"order_creation_state_machine": "type"}, Query().user_id == m.user_id)
        elif state == "type":
            if m.text == "Купить":
                self._sessions[m.user_id]["order"].type = OrderType.BUY
                self._app_db.update(
                    {"order": {**self._app_db.search(Query().user_id == m.user_id)[0]["order"], "type": "BUY"}},
                    Query().user_id == m.user_id,
                )
            elif m.text == "Продать":
                self._sessions[m.user_id]["order"].type = OrderType.SELL
                self._app_db.update(
                    {"order": {**self._app_db.search(Query().user_id == m.user_id)[0]["order"], "type": "SELL"}},
                    Query().user_id == m.user_id,
                )
            else:
                raise ValueError(f"Invalid order type: {m.text}")
            self._sessions[m.user_id]["order_creation_state_machine"].set_type()
            self._app_db.update({"order_creation_state_machine": "currency_from"}, Query().user_id == m.user_id)
            text = "Выберите исходную валюту"
            reply_markup = [["RUB"]]
        elif state == "currency_from":
            self._validator.validate_currency_from(m.text)
            self._sessions[m.user_id]["order"].currency_from = m.text
            self._sessions[m.user_id]["order_creation_state_machine"].set_currency_from()
            self._app_db.update(
                {"order": {**self._app_db.search(Query().user_id == m.user_id)[0]["order"], "currency_from": m.text}},
                Query().user_id == m.user_id,
            )
            self._app_db.update({"order_creation_state_machine": "currency_to"}, Query().user_id == m.user_id)
            text = "Выберите целевую валюту"
            reply_markup = [["AMD"]]
        elif state == "currency_to":
            self._validator.validate_currency_to(m.text)
            self._sessions[m.user_id]["order"].currency_to = m.text
            self._sessions[m.user_id]["order_creation_state_machine"].set_currency_to()
            self._app_db.update(
                {"order": {**self._app_db.search(Query().user_id == m.user_id)[0]["order"], "currency_to": m.text}},
                Query().user_id == m.user_id,
            )
            self._app_db.update({"order_creation_state_machine": "amount"}, Query().user_id == m.user_id)
            text = "Введите сумму для обмена"
            reply_markup = None
        elif state == "amount":
            self._validator.validate_amount(m.text)
            self._sessions[m.user_id]["order"].amount_initial = Decimal(m.text)
            self._sessions[m.user_id]["order_creation_state_machine"].set_amount()
            self._app_db.update(
                {"order": {**self._app_db.search(Query().user_id == m.user_id)[0]["order"], "amount_initial": m.text}},
                Query().user_id == m.user_id,
            )
            self._app_db.update({"order_creation_state_machine": "price"}, Query().user_id == m.user_id)
            text = "Введите желаемую цену за единицу валюты (курс обмена)"
            reply_markup = None
        elif state == "price":
            self._validator.validate_price(m.text)
            self._sessions[m.user_id]["order"].price = Decimal(m.text)
            self._sessions[m.user_id]["order_creation_state_machine"].set_price()
            self._app_db.update(
                {"order": {**self._app_db.search(Query().user_id == m.user_id)[0]["order"], "price": m.text}},
                Query().user_id == m.user_id,
            )
            self._app_db.update({"order_creation_state_machine": "min_op_threshold"}, Query().user_id == m.user_id)
            text = "Введите минимальный порог операции"
            reply_markup = None
        elif state == "min_op_threshold":
            self._validator.validate_min_op_threshold(m.text, self._sessions[m.user_id]["order"].amount_initial)
            self._sessions[m.user_id]["order"].min_op_threshold = Decimal(m.text)
            self._sessions[m.user_id]["order_creation_state_machine"].set_min_op_threshold()
            self._app_db.update(
                {
                    "order": {
                        **self._app_db.search(Query().user_id == m.user_id)[0]["order"],
                        "min_op_threshold": m.text,
                    }
                },
                Query().user_id == m.user_id,
            )
            self._app_db.update({"order_creation_state_machine": "lifetime"}, Query().user_id == m.user_id)
            text = "Введите время жизни заявки в часах (не более 48)"
            reply_markup = None
        elif state == "lifetime":
            self._validator.validate_lifetime(m.text)
            self._sessions[m.user_id]["order"].lifetime_sec = int(m.text) * 3600
            self._sessions[m.user_id]["order_creation_state_machine"].set_lifetime()
            self._app_db.update(
                {
                    "order": {
                        **self._app_db.search(Query().user_id == m.user_id)[0]["order"],
                        "lifetime_sec": int(m.text) * 3600,
                    }
                },
                Query().user_id == m.user_id,
            )
            self._app_db.update({"order_creation_state_machine": "confirm"}, Query().user_id == m.user_id)
            text = "Подтвердите создание заявки"
            reply_markup = [["Подтвердить"], ["Отменить"]]
        elif state == "confirm":
            if m.text == "Подтвердить":
                self._sessions[m.user_id]["order"].amount_left = self._sessions[m.user_id]["order"].amount_initial
                self._ex.on_new_order(self._sessions[m.user_id]["order"])
                text = "Заявка создана"
            elif m.text == "Отменить":
                text = "Заявка отменена"
            else:
                raise ValueError(f"Invalid command: {m.text}")
            reply_markup = self.MAIN_MENU_BUTTONS
            self._sessions[m.user_id]["order_creation_state_machine"] = None
            self._sessions[m.user_id]["order"] = None
            del self._sessions[m.user_id]
            self._app_db.remove(Query().user_id == m.user_id)

        self._send_message(m.user_id, m.user_name, text, reply_markup=reply_markup)

    def _handle_list_command(self, m: TgMsg):
        orders = self._ex.list_orders_for_user(User(m.user_id, m.user_name))
        if not orders:
            self._send_message(
                m.user_id, m.user_name, "You don't have any active orders", reply_markup=self.MAIN_MENU_BUTTONS
            )
        else:
            text = (
                "Your orders:\n"
                + "\n".join(
                    [
                        f"\tid: {o._id} ({o.type.name} {o.amount_left} RUB * {o.price} AMD "
                        f"min_amt {o.min_op_threshold} lifetime_h {int(o.lifetime_sec/3600)} "
                        f"[until: {self._convert_to_utc(o.creation_time, o.lifetime_sec)}])"
                        for o in orders
                    ]
                )
                + "\n\nto remove an order, use /remove <id>"
            )
            self._send_message(m.user_id, m.user_name, text)

    def _handle_remove_command(self, m: TgMsg, params: list):
        self._validator.validate_remove_command_params(params, self._ex, m.user_id)
        remove_order_id = int(params[0])
        self._ex.remove_order(remove_order_id)
        self._send_message(m.user_id, m.user_name, f"Order with id {remove_order_id} was removed")

    @staticmethod
    def _convert_to_utc(creation_time, lifetime_sec):
        return datetime.datetime.fromtimestamp(creation_time + lifetime_sec, datetime.UTC)

    def _on_match(self, m: Match):
        buyer_id = m.buy_order.user.id
        buyer_name = m.buy_order.user.name
        seller_id = m.sell_order.user.id
        seller_name = m.sell_order.user.name
        message_buyer = (
            f"Go and buy {m.amount} RUB from @{seller_name} for {m.price} per unit (you should send"
            f" {m.price * m.amount:.2f} AMD, you will get {m.amount:.2f} RUB)"
        )
        message_seller = (
            f"You should sell {m.amount} RUB to @{buyer_name} for {m.price} per unit (you should send"
            f" {m.amount:.2f} RUB, you will get {m.price * m.amount:.2f} AMD)"
        )
        self._tg.send_message(TgMsg(buyer_id, buyer_name, message_buyer))
        self._tg.send_message(TgMsg(seller_id, seller_name, message_seller))
