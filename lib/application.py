from typing import Optional
from decimal import Decimal, InvalidOperation
import datetime
import os

from tinydb import TinyDB, Query
from dotenv import load_dotenv

from .db import Db
from .tg import Tg, TgIncomingMsg, TgOutgoingMsg

from .exchange import Exchange
from .gsheets_loger import GSheetsLoger
from .data import Match, Order, User, OrderType
from .logger import get_logger
from .statemachines import OrderCreation

from .currency_rates import CurrencyConverter, CurrencyFreaksClient, CurrencyMockClient
from .config import ORDER_LIFETIME_LIMIT

from bootshop.stories import OutMessage, Command, Message, ButtonAction
from lib import dialogs
from .lazy_load import LazyMessageLoader

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
            if Decimal(amount) <= 0:
                raise ValueError("Amount cannot be negative or zero")
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {amount}")

    def validate_currency_from(self, currency_from: str):
        if currency_from.lower() not in ["rub"]:
            raise ValueError(f"Invalid currency: {currency_from}")

    def validate_currency_to(self, currency_to: str):
        if currency_to.lower() not in ["amd"]:
            raise ValueError(f"Invalid currency: {currency_to}")

    def validate_price(self, price: str | Decimal):
        try:
            price = Decimal(price)
            if price != price.quantize(Decimal("0.0001")):
                raise ValueError(
                    f"Price has more than four digits after the decimal point: {price}"
                )
            elif price <= 0:
                raise ValueError("Price cannot be negative or zero")
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {price}")

    def validate_min_op_threshold(
        self, min_op_threshold: str | Decimal, amount: str | Decimal
    ):
        try:
            min_op_threshold = Decimal(min_op_threshold)
            amount = Decimal(amount)
            if min_op_threshold < 0:
                raise ValueError("Minimum operational threshold cannot be negative")
            if min_op_threshold > amount:
                raise ValueError(
                    "Minimum operational threshold cannot be greater than the amount"
                )
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {min_op_threshold}")

    def validate_lifetime(self, lifetime: str, limit_sec=ORDER_LIFETIME_LIMIT):
        if not lifetime.isnumeric():
            raise ValueError(f"Invalid lifetime: {lifetime}")
        if int(lifetime) < 0:
            raise ValueError("Lifetime cannot be negative")
        if int(lifetime) > (limit_sec // 3600):
            raise ValueError(
                f"Lifetime cannot be greater than {limit_sec // 3600} hours"
            )

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
    MAIN_MENU_BUTTONS = [
        ["Create order", "My orders"],
        ["Statistics", "Help"],
    ]  # TODO: 'История заявок'
    # TODO:
    # - add lifetime to orders

    def __init__(
        self,
        db: Db,
        tg: Tg,
        zmq_orders_log_endpoint=None,
        log_spreadsheet_key=None,
        debug_mode=False,
    ):
        self._db = db
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message
        self._sessions2: dict[int, dialogs.Main] = {}

        self.start_message_loader = LazyMessageLoader(
            os.path.join(os.path.dirname(__file__), "tg_messages", "start_message.md")
        )
        self.help_message_loader = LazyMessageLoader(
            os.path.join(os.path.dirname(__file__), "tg_messages", "help_message.md")
        )
        self.disclaimer_message_loader = LazyMessageLoader(
            os.path.join(
                os.path.dirname(__file__), "tg_messages", "disclaimer_message.md"
            )
        )

        if debug_mode is False:
            load_dotenv()
            currency_client_api_key = os.getenv("EXCH_CURRENCYFREAKS_TOKEN")
            currency_client: CurrencyFreaksClient | CurrencyMockClient = (
                CurrencyFreaksClient(currency_client_api_key)
            )
            currency_converter = CurrencyConverter(currency_client)
        else:
            currency_client = CurrencyMockClient()
            currency_converter = CurrencyConverter(currency_client)

        self._ex = Exchange(
            self._db, currency_converter, self._on_match, zmq_orders_log_endpoint
        )
        self._sessions: dict = {}
        self._app_db = TinyDB("./tg_data/app_db.json")

        if zmq_orders_log_endpoint:
            assert log_spreadsheet_key is not None
            worksheet_title = os.getenv("GOOGLE_SPREADSHEET_SHEET_TITLE", None)
            self._loger = GSheetsLoger(
                zmq_orders_log_endpoint, log_spreadsheet_key, worksheet_title
            )
            self._loger.start()
        self._validator = Validator()

    def shutdown(self):
        self._loger.stop()

    def _send_message(
        self, user_id, user_name, message, parse_mode=None, reply_markup=None
    ):
        self._tg.send_message(
            TgOutgoingMsg(
                user_id,
                user_name,
                message,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            ),
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

    def _check_unfinished_session(self, m: TgIncomingMsg):
        user_query = self._app_db.search(Query().user_id == m.user_id)
        if user_query:
            if user_query[0].get("order_creation_state_machine"):
                return user_query[0]

    def _on_incoming_tg_message2(self, m: TgIncomingMsg):
        try:
            _root = self._sessions2[m.user_id]
        except KeyError:
            _root = dialogs.Main()
            self._sessions2[m.user_id] = _root
        top = _root.get_top()
        out: Optional[OutMessage] = None

        pp = m.text.lower().strip().split(" ")
        command = pp[0]
        args = pp[1:]
        if command.startswith("/"):
            command = command[1:]
            out = top.process_event(Command(m.user_id, name=command, args=args))
        else:
            out = top.process_event(Message(m.user_id, text=m.text))
        while out:
            rm = [
                [b.text for b in line] for line in out.buttons
            ]  # FIXME: use inline keyboard here
            self._send_message(
                m.user_id,
                m.user_name,
                out.text,
                reply_markup=rm,
                parse_mode=out.parse_mode,
            )
            out = out.next

    def _on_incoming_tg_message(self, m: TgIncomingMsg):
        try:
            if m.user_id < 0:
                raise ValueError("We don't work with groups yet")

            if m.text == "Create order":
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
                self._on_incoming_tg_message2(m)
                return
                with open("./lib/tg_messages/start_message.md", "r") as f:
                    tg_start_message = f.read().strip()
                self._send_message(
                    m.user_id,
                    m.user_name,
                    self.start_message_loader.message,
                    parse_mode="Markdown",
                    reply_markup=self.MAIN_MENU_BUTTONS,
                )
            elif command == "/help" or m.text == "Help":
                self._on_incoming_tg_message2(m)
                return
                self._send_message(
                    m.user_id,
                    m.user_name,
                    self.help_message_loader.message,
                    parse_mode="Markdown",
                    reply_markup=self.MAIN_MENU_BUTTONS,
                )
            elif command == "/new_dialogs" or m.text == "Help":
                self._on_incoming_tg_message2(m)
            elif command == "/add":
                self._handle_add_command(m, params)
            elif command == "/list" or m.text == "My orders":
                self._handle_list_command(m)
            elif command == "/remove":
                self._handle_remove_command(m, params)
            elif command == "/stat" or m.text == "Statistics":
                self._handle_stat_command(m)
            else:
                raise ValueError(f"Invalid command: {command}")

        except ValueError as e:
            self._send_message(m.user_id, m.user_name, f"Error: {str(e)}")

    def _handle_stat_command(self, m: TgIncomingMsg, statemachine: bool = False):
        self._ex._check_order_lifetime()
        text = self._ex.get_stats()["text"]
        if statemachine:
            reply_markup = [["Cancel"]]
        else:
            reply_markup = self.MAIN_MENU_BUTTONS
        self._send_message(m.user_id, m.user_name, text, reply_markup=reply_markup)

    def _handle_add_command(self, m: TgIncomingMsg, params: list):
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
        self._send_message(
            m.user_id,
            m.user_name,
            "We get your order",
            reply_markup=self.MAIN_MENU_BUTTONS,
        )
        self._ex.on_new_order(o)

    def _prepare_order_creation(self, m: TgIncomingMsg, session=None):
        self._sessions[m.user_id] = {
            "order_creation_state_machine": OrderCreation(m.user_id),
            # TODO: class Order must not allow None values.
            # Therefore we need to create a new class that will be used as a draft of the order.
            "order": Order(
                User(m.user_id, m.user_name),
                OrderType.BUY,
                Decimal(-1),
                Decimal(-1),
                Decimal(-1),
                0,
            ),
        }
        if session:
            self._sessions[m.user_id]["order_creation_state_machine"].state = session[
                "order_creation_state_machine"
            ]
            for key, value in session["order"].items():
                if key == "user_id" or key == "user_name":
                    continue
                elif key == "type":
                    self._sessions[m.user_id]["order"].type = OrderType[value]
                elif key in [
                    "amount_initial",
                    "amount_left",
                    "price",
                    "min_op_threshold",
                    "relative_rate",
                ]:
                    self._sessions[m.user_id]["order"].__setattr__(key, Decimal(value))
                else:
                    self._sessions[m.user_id]["order"].__setattr__(key, value)
        else:
            self._app_db.insert({"user_id": m.user_id, "user_name": m.user_name})
            self._app_db.update(
                {"order_creation_state_machine": "start"}, Query().user_id == m.user_id
            )
            self._app_db.update({"order": "start"}, Query().user_id == m.user_id)

    def _handle_order_creation_sm(self, m: TgIncomingMsg):
        if m.text == "Cancel":
            reply_markup: list | None = self.MAIN_MENU_BUTTONS
            self._sessions[m.user_id]["order_creation_state_machine"] = None
            self._sessions[m.user_id]["order"] = None
            del self._sessions[m.user_id]
            self._app_db.remove(Query().user_id == m.user_id)
            self._send_message(
                m.user_id,
                m.user_name,
                "The order was canceled",
                reply_markup=reply_markup,
            )
            return
        elif m.text == "/stat":
            self._handle_stat_command(m, statemachine=True)
            return
        state = self._sessions[m.user_id]["order_creation_state_machine"].state
        if state == "start":
            text = self._ex.get_stats()["short_text"]
            text += "\n\nChoose the type of order"
            reply_markup = [["Buy rubles", "Sell rubles"]]
            self._sessions[m.user_id]["order_creation_state_machine"].new_order()
            self._app_db.update(
                {"order": {"user_id": m.user_id, "user_name": m.user_name}},
                Query().user_id == m.user_id,
            )
            self._app_db.update(
                {"order_creation_state_machine": "type"}, Query().user_id == m.user_id
            )
        elif state == "type":
            if m.text == "Buy rubles":
                self._sessions[m.user_id]["order"].type = OrderType.BUY
                self._app_db.update(
                    {
                        "order": {
                            **self._app_db.search(Query().user_id == m.user_id)[0][
                                "order"
                            ],
                            "type": "BUY",
                        }
                    },
                    Query().user_id == m.user_id,
                )
            elif m.text == "Sell rubles":
                self._sessions[m.user_id]["order"].type = OrderType.SELL
                self._app_db.update(
                    {
                        "order": {
                            **self._app_db.search(Query().user_id == m.user_id)[0][
                                "order"
                            ],
                            "type": "SELL",
                        }
                    },
                    Query().user_id == m.user_id,
                )
            else:
                raise ValueError(f"Invalid order type: {m.text}")
            # self._sessions[m.user_id]["order_creation_state_machine"].set_type()
            self._sessions[m.user_id]["order_creation_state_machine"].set_type_rubamd()
            # self._app_db.update({"order_creation_state_machine": "currency_from"}, Query().user_id == m.user_id)
            self._app_db.update(
                {"order_creation_state_machine": "amount"}, Query().user_id == m.user_id
            )
            # text = "Выберите исходную валюту"
            # reply_markup = [["RUB"]]
            text = "Enter the amount to exchange (RUB)"
            reply_markup = None
        elif state == "currency_from":  # Currently not used
            self._validator.validate_currency_from(m.text)
            self._sessions[m.user_id]["order"].currency_from = m.text
            self._sessions[m.user_id][
                "order_creation_state_machine"
            ].set_currency_from()
            self._app_db.update(
                {
                    "order": {
                        **self._app_db.search(Query().user_id == m.user_id)[0]["order"],
                        "currency_from": m.text,
                    }
                },
                Query().user_id == m.user_id,
            )
            self._app_db.update(
                {"order_creation_state_machine": "currency_to"},
                Query().user_id == m.user_id,
            )
            text = "Выберите целевую валюту"
            reply_markup = [["AMD"]]
        elif state == "currency_to":  # Currently not used
            self._validator.validate_currency_to(m.text)
            self._sessions[m.user_id]["order"].currency_to = m.text
            self._sessions[m.user_id]["order_creation_state_machine"].set_currency_to()
            self._app_db.update(
                {
                    "order": {
                        **self._app_db.search(Query().user_id == m.user_id)[0]["order"],
                        "currency_to": m.text,
                    }
                },
                Query().user_id == m.user_id,
            )
            self._app_db.update(
                {"order_creation_state_machine": "amount"}, Query().user_id == m.user_id
            )
            text = "Enter the amount to exchange (RUB)"
            reply_markup = None
        elif state == "amount":
            self._validator.validate_amount(m.text)
            self._sessions[m.user_id]["order"].amount_initial = Decimal(m.text)
            self._sessions[m.user_id]["order_creation_state_machine"].set_amount()
            self._app_db.update(
                {
                    "order": {
                        **self._app_db.search(Query().user_id == m.user_id)[0]["order"],
                        "amount_initial": m.text,
                    }
                },
                Query().user_id == m.user_id,
            )
            self._app_db.update(
                {"order_creation_state_machine": "type_price"},
                Query().user_id == m.user_id,
            )
            text = "Choose the type of rate"
            reply_markup = [["Absolute", "Relative to the exchange"]]
        elif state == "type_price":
            # FIXME
            # self._validator.validate_amount(m.text)

            if m.text == "Absolute":
                self._sessions[m.user_id]["order"].relative_rate = Decimal("-1.0")

                self._app_db.update(
                    {
                        "order": {
                            **self._app_db.search(Query().user_id == m.user_id)[0][
                                "order"
                            ],
                            "type_price": "Absolute",
                        }
                    },  # FIXME
                    Query().user_id == m.user_id,
                )
                text = "Enter the desired exchange rate in AMD/RUB. For example: 4.54"
            elif m.text == "Relative to the exchange":
                self._sessions[m.user_id]["order"].relative_rate = None
                # self._sessions[m.user_id]["order"].type = OrderType.SELL
                self._app_db.update(
                    {
                        "order": {
                            **self._app_db.search(Query().user_id == m.user_id)[0][
                                "order"
                            ],
                            "type_price": "Relative",
                        }
                    },
                    Query().user_id == m.user_id,
                )
                text = (
                    "Enter the desired exchange rate relative to the exchange. For example: 1.01 "
                    "(above the exchange rate by 1%) or 0.98 (below the exchange rate by 2%).\n"
                    f"Current exchange rate: {self._ex.currency_rate['rate']} AMD/RUB"
                )
            else:
                raise ValueError(f"Invalid type_price: {m.text}")

            self._sessions[m.user_id]["order_creation_state_machine"].set_type_price()
            self._app_db.update(
                {"order_creation_state_machine": "price"}, Query().user_id == m.user_id
            )
            reply_markup = None
        elif state == "price":
            self._validator.validate_price(m.text)
            if self._sessions[m.user_id]["order"].relative_rate is None:
                # relative rate
                self._sessions[m.user_id]["order"].price = Decimal(
                    Decimal(m.text) * self._ex.currency_rate["rate"]
                ).quantize(Decimal("0.0001"))
                self._sessions[m.user_id]["order"].relative_rate = Decimal(m.text)
            else:
                # absolute rate
                self._sessions[m.user_id]["order"].price = Decimal(m.text)

            self._sessions[m.user_id]["order_creation_state_machine"].set_price()
            self._app_db.update(
                {
                    "order": {
                        **self._app_db.search(Query().user_id == m.user_id)[0]["order"],
                        "price": str(self._sessions[m.user_id]["order"].price),
                    }
                },
                Query().user_id == m.user_id,
            )
            self._app_db.update(
                {
                    "order": {
                        **self._app_db.search(Query().user_id == m.user_id)[0]["order"],
                        "relative_rate": str(
                            self._sessions[m.user_id]["order"].relative_rate
                        ),
                    }
                },
                Query().user_id == m.user_id,
            )
            self._app_db.update(
                {"order_creation_state_machine": "min_op_threshold"},
                Query().user_id == m.user_id,
            )
            text = "Enter the minimum operational threshold in RUB"
            reply_markup = None
        elif state == "min_op_threshold":
            self._validator.validate_min_op_threshold(
                m.text, self._sessions[m.user_id]["order"].amount_initial
            )
            self._sessions[m.user_id]["order"].min_op_threshold = Decimal(m.text)
            self._sessions[m.user_id][
                "order_creation_state_machine"
            ].set_min_op_threshold()
            self._app_db.update(
                {
                    "order": {
                        **self._app_db.search(Query().user_id == m.user_id)[0]["order"],
                        "min_op_threshold": m.text,
                    }
                },
                Query().user_id == m.user_id,
            )
            self._app_db.update(
                {"order_creation_state_machine": "lifetime"},
                Query().user_id == m.user_id,
            )
            text = "Enter the lifetime of the order in hours"
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
            self._app_db.update(
                {"order_creation_state_machine": "confirm"},
                Query().user_id == m.user_id,
            )
            text_about_rate = ""
            if self._sessions[m.user_id]["order"].relative_rate == -1.0:
                text_about_rate = (
                    f"price: {self._sessions[m.user_id]['order'].price} AMD/RUB"
                )
            else:
                text_about_rate = (
                    f"price: {self._sessions[m.user_id]['order'].relative_rate} RELATIVE "
                    f"(current value: {self._sessions[m.user_id]['order'].price} AMD/RUB)"
                )
            text = (
                "Confirm the order:"
                f"\n\ttype: {self._sessions[m.user_id]['order'].type.name}"
                f"\n\tamount: {self._sessions[m.user_id]['order'].amount_initial} RUB"
                f"\n\t{text_about_rate}"
                f"\n\tmin_op_threshold: {self._sessions[m.user_id]['order'].min_op_threshold} RUB"
                f"\n\tlifetime: {self._sessions[m.user_id]['order'].lifetime_sec // 3600} hours"
            )
            reply_markup = [["Confirm"]]  # , ["Cancel"]]
        elif state == "confirm":
            if m.text == "Confirm":
                self._sessions[m.user_id]["order"].amount_left = self._sessions[
                    m.user_id
                ]["order"].amount_initial
                self._ex.on_new_order(self._sessions[m.user_id]["order"])
                text = "The order was created"
            elif m.text == "Cancel":
                text = "The order was canceled"
            else:
                raise ValueError(f"Invalid command: {m.text}")
            reply_markup = self.MAIN_MENU_BUTTONS
            self._sessions[m.user_id]["order_creation_state_machine"] = None
            self._sessions[m.user_id]["order"] = None
            del self._sessions[m.user_id]
            self._app_db.remove(Query().user_id == m.user_id)

        if reply_markup == self.MAIN_MENU_BUTTONS:
            pass
        elif reply_markup:
            reply_markup += [["Cancel"]]
        else:
            reply_markup = [["Cancel"]]
        self._send_message(m.user_id, m.user_name, text, reply_markup=reply_markup)

    def _handle_list_command(self, m: TgIncomingMsg):
        orders = self._ex.list_orders_for_user(User(m.user_id, m.user_name))
        if not orders:
            self._send_message(
                m.user_id,
                m.user_name,
                "You don't have any active orders",
                reply_markup=self.MAIN_MENU_BUTTONS,
            )
        else:
            text = "Your orders:\n"
            for o in orders:
                if o.relative_rate == -1.0:
                    text_about_rate = f"{o.price} AMD"
                else:
                    text_about_rate = (
                        f"{o.relative_rate} RELATIVE (current value: {o.price} AMD)"
                    )

                text += (
                    "\n"
                    f"\tid: {o._id} ({o.type.name} {o.amount_left} RUB * {text_about_rate} "
                    f"min_amt {o.min_op_threshold} lifetime_h {o.lifetime_sec // 3600} "
                    f"[until: {self._convert_to_utc(o.creation_time, o.lifetime_sec)}])"
                )

            text += "\n\nto remove an order, use /remove <id>"
            self._send_message(
                m.user_id, m.user_name, text, reply_markup=self.MAIN_MENU_BUTTONS
            )

    def _handle_remove_command(self, m: TgIncomingMsg, params: list):
        self._validator.validate_remove_command_params(params, self._ex, m.user_id)
        remove_order_id = int(params[0])
        self._ex.remove_order(remove_order_id)
        self._send_message(
            m.user_id, m.user_name, f"Order with id {remove_order_id} was removed"
        )

    @staticmethod
    def _convert_to_utc(creation_time, lifetime_sec):
        return datetime.datetime.fromtimestamp(
            creation_time + lifetime_sec, datetime.UTC
        )

    def _on_match(self, m: Match):
        buyer_id = m.buy_order.user.id
        buyer_name = m.buy_order.user.name
        seller_id = m.sell_order.user.id
        seller_name = m.sell_order.user.name
        message_buyer = (
            f"Go and buy {m.amount} RUB from @{seller_name} for {m.price} per unit (you should send"
            f" {m.price * m.amount:.2f} AMD, you will get {m.amount:.2f} RUB)"
            f"\n\n{self.disclaimer_message_loader.message}"
        )
        message_seller = (
            f"You should sell {m.amount} RUB to @{buyer_name} for {m.price} per unit (you should send"
            f" {m.amount:.2f} RUB, you will get {m.price * m.amount:.2f} AMD)"
            f"\n\n{self.disclaimer_message_loader.message}"
        )
        self._tg.send_message(TgOutgoingMsg(buyer_id, buyer_name, message_buyer))
        self._tg.send_message(TgOutgoingMsg(seller_id, seller_name, message_seller))
