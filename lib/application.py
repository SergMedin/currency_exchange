from decimal import Decimal
import datetime
import os
import logging

from dotenv import load_dotenv

from bootshop.stories import (
    OutMessage,
    Command,
    Message,
    ButtonAction,
    Button,
)  # FIXME: move this stuff to the dedicated repo
from . import dialogs
from . import business_rules
from .db import Db
from .tg import Tg, TgIncomingMsg, TgOutgoingMsg, InlineKeyboardButton
from .exchange import Exchange
from .gsheets_loger import GSheetsLoger
from .data import Match, Order, User, OrderType
from .currency_rates import CurrencyConverter, CurrencyFreaksClient, CurrencyMockClient
from .lazy_load import LazyMessageLoader


class Application:
    def __init__(
        self,
        db: Db,
        tg: Tg,
        zmq_orders_log_endpoint=None,
        log_spreadsheet_key=None,
    ):
        self._db = db
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message

        # FIXME: should be persistent, LRU with limit, created only when needed
        self._sessions: dict[int, dialogs.Main] = {}

        # FIXME: move it out of here
        self.disclaimer_message_loader = LazyMessageLoader(
            os.path.join(
                os.path.dirname(__file__),
                "dialogs",
                "tg_messages",
                "disclaimer_message.md",
            )
        )

        # FIXME: remove this outside of the module
        if "EXCH_CURRENCYFREAKS_TOKEN" in os.environ:
            load_dotenv()
            currency_client_api_key = os.environ["EXCH_CURRENCYFREAKS_TOKEN"]
            currency_client: CurrencyFreaksClient | CurrencyMockClient = CurrencyFreaksClient(currency_client_api_key)
            currency_converter = CurrencyConverter(currency_client)
        else:
            currency_client = CurrencyMockClient()
            currency_converter = CurrencyConverter(currency_client)

        self._ex = Exchange(self._db, currency_converter, self._on_match, zmq_orders_log_endpoint)

        # FIXME: no env vars reading stuff should be here
        if zmq_orders_log_endpoint:
            assert log_spreadsheet_key is not None
            worksheet_title = os.getenv("GOOGLE_SPREADSHEET_SHEET_TITLE", None)
            self._loger = GSheetsLoger(zmq_orders_log_endpoint, log_spreadsheet_key, worksheet_title)
            self._loger.start()

        self._validator = business_rules.Validator()

    def shutdown(self):
        self._loger.stop()

    def _send_message(
        self,
        user_id,
        user_name,
        message,
        parse_mode=None,
        keyboard_below=None,
        inline_keyboard: list[list[Button]] | None = None,
    ):
        if inline_keyboard:
            keyboard = [
                [InlineKeyboardButton(b.text, callback_data=b.action) for b in line] for line in inline_keyboard
            ]
        else:
            keyboard = None

        m = TgOutgoingMsg(
            user_id,
            user_name,
            message,
            keyboard_below=keyboard_below,
            parse_mode=parse_mode,
            inline_keyboard=keyboard,
        )
        self._tg.send_message(m)

    def _process_incoming_tg_message(self, m: TgIncomingMsg):
        if m.user_id < 0:
            raise ValueError("We don't work with groups yet")

        try:
            _root = self._sessions[m.user_id]
        except KeyError:
            _root = dialogs.Main(dialogs.Session(m.user_id, m.user_name, self._ex))
            self._sessions[m.user_id] = _root

        top = _root.get_current_active()
        out: OutMessage | None
        event: ButtonAction | Command | Message

        if m.keyboard_callback:
            event = ButtonAction(m.user_id, name=m.keyboard_callback)
        elif m.text.startswith("/"):
            # FIXME: args must not be converted to lower
            pp = m.text.lower().strip().split(" ")
            command = pp[0]
            args = pp[1:]

            # FIXME: remove this
            if command == "/add":
                return self._handle_add_command(m, args)
            elif command == "/remove":
                return self._handle_remove_command(m, args)

            command = command[1:]
            event = Command(m.user_id, name=command, args=args)
        else:
            event = Message(m.user_id, text=m.text)

        logging.info(f"Event: {event}; top: {top}")
        out = top.process_event(event)
        assert out is not None

        while out:
            logging.info(f"Out: {out}")

            buttons_below = None
            if out.buttons_below is not None:
                buttons_below = [[b.text for b in line] for line in out.buttons_below]

            self._send_message(
                m.user_id,
                m.user_name,
                out.text,
                parse_mode=out.parse_mode,
                keyboard_below=buttons_below,
                inline_keyboard=out.buttons,
            )
            out = out.next

    def _on_incoming_tg_message(self, m: TgIncomingMsg):
        logging.info(f"Got message: {m}")
        try:
            return self._process_incoming_tg_message(m)
        except ValueError as e:
            self._send_message(m.user_id, m.user_name, f"Error: {str(e)}")

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
            "We got your order",
        )
        self._ex.place_order(o)

    def _handle_remove_command(self, m: TgIncomingMsg, params: list):
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
            f"Вы можете приобрести {m.amount} RUB у @{seller_name} по цене {m.price} за единицу (вы должны отправить"
            f" {m.price * m.amount:.2f} AMD, вы получите {m.amount:.2f} RUB)"
            f"\n\n{self.disclaimer_message_loader.message}"
        )
        message_seller = (
            f"Вы можете продать {m.amount} RUB @{buyer_name} по цене {m.price} за единицу (вы должны отправить"
            f" {m.amount:.2f} RUB, вы получите {m.price * m.amount:.2f} AMD)"
            f"\n\n{self.disclaimer_message_loader.message}"
        )
        self._tg.send_message(TgOutgoingMsg(buyer_id, buyer_name, message_buyer))
        self._tg.send_message(TgOutgoingMsg(seller_id, seller_name, message_seller))

        # Notify admins
        if self._tg.admin_contacts is not None:
            message_for_admins = "match!\n\n"
            for attr, value in vars(m).items():
                message_for_admins += f"{attr}:\n{value}\n\n"

            for admin_contact in self._tg.admin_contacts:
                self._tg.send_message(TgOutgoingMsg(admin_contact, None, message_for_admins))
