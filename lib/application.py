from typing import Optional
from decimal import Decimal
import datetime
import os
import logging


from .botlib.stories import (
    OutMessage,
    Command,
    Message,
    ButtonAction,
    Button,
)  # FIXME: move this stuff to the dedicated repo
from . import dialogs
from . import business_rules
from .db import Db
from .botlib.tg import Tg, TgIncomingMsg, TgOutgoingMsg, InlineKeyboardButton
from .exchange import Exchange
from .gsheets_loger import GSheetsLoger
from .data import Match, Order, User, OrderType
from .currency_rates import CurrencyConverter, CurrencyFreaksClient, CurrencyMockClient
from .lazy_load import LazyMessageLoader
from .rep_sys import ReputationSystem


class Application:
    def __init__(
        self,
        db: Db,
        tg: Tg,
        currency_client: CurrencyFreaksClient | CurrencyMockClient,
        rep_sys: ReputationSystem,
        zmq_orders_log_endpoint=None,
        log_spreadsheet_key=None,
        admin_contacts: Optional[list[int]] = None,
    ):
        self._admin_contacts = admin_contacts
        self._db = db
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message
        self._rep_sys = rep_sys

        # FIXME: should be (1) persistent, (2) LRU with limit, (3) created only when really needed
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

        currency_converter = CurrencyConverter(currency_client)
        self._ex = Exchange(
            self._db, currency_converter, self._on_match, zmq_orders_log_endpoint
        )

        # FIXME: no env vars reading stuff should be here
        if zmq_orders_log_endpoint:
            assert log_spreadsheet_key is not None
            worksheet_title = os.getenv("GOOGLE_SPREADSHEET_SHEET_TITLE", None)
            self._loger = GSheetsLoger(
                zmq_orders_log_endpoint, log_spreadsheet_key, worksheet_title
            )
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
                [InlineKeyboardButton(b.text, callback_data=b.action) for b in line]
                for line in inline_keyboard
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

    def _process_incoming_tg_message(self, m: TgIncomingMsg) -> list[TgOutgoingMsg]:
        if m.user_id < 0:
            raise ValueError("We don't work with groups yet")

        try:
            _root = self._sessions[m.user_id]
        except KeyError:
            session = dialogs.Session(
                m.user_id, m.user_name, self._ex, rep_sys=self._rep_sys
            )
            _root = dialogs.Main(session)
            self._sessions[m.user_id] = _root

        top = _root.get_current_active()
        out: OutMessage | None
        event: ButtonAction | Command | Message

        if m.keyboard_callback:
            event = ButtonAction(m.message_id, m.user_id, name=m.keyboard_callback)
        elif m.text.startswith("/"):
            # FIXME: args must not be converted to lower
            pp = m.text.lower().strip().split(" ")
            command = pp[0]
            args = pp[1:]

            # FIXME: remove this
            if command == "/add":
                self._handle_add_command(m, args)
                return []
            elif command == "/remove":
                self._handle_remove_command(m, args)
                return []

            command = command[1:]
            event = Command(m.message_id, m.user_id, name=command, args=args)
        else:
            event = Message(m.message_id, m.user_id, text=m.text)

        logging.info(f"Event: {event}; top: {top}")
        out = top.process_event(event)
        assert out is not None

        tg_out_messages: list[TgOutgoingMsg] = []
        while out:
            logging.info(f"Out message: {out}")
            keyboard_below = None
            if out.buttons_below is not None:
                keyboard_below = [[b.text for b in line] for line in out.buttons_below]
            inline_keyboard = None
            if out.buttons:
                inline_keyboard = [
                    [InlineKeyboardButton(b.text, callback_data=b.action) for b in line]
                    for line in out.buttons
                ]
            tg_out = TgOutgoingMsg(
                m.user_id,
                m.user_name,
                out.text,
                keyboard_below=keyboard_below,
                parse_mode=out.parse_mode,
                inline_keyboard=inline_keyboard,
                edit_message_with_id=out.edit_message_with_id,
            )
            tg_out_messages.append(tg_out)
            out = out.next

        return tg_out_messages

    def _on_incoming_tg_message(self, m: TgIncomingMsg) -> list[TgOutgoingMsg]:
        logging.info(f"Got message: {m}")
        try:
            res = self._process_incoming_tg_message(m)
        except ValueError as e:
            res = [TgOutgoingMsg(m.user_id, m.user_name, f"Error: {str(e)}")]
        return res

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
        self._notyfy_admins(m)

    def _notyfy_admins(self, m: Match):
        def render_order(o: Order) -> str:
            return (
                f"\tuser: @{o.user.name} ({o.user.id})\n"
                f"\tprice: {o.price:.4f} AMD/RUB\n"
                f"\tamount_initial: {o.amount_initial:.2f} RUB\n"
                f"\tamount_left: {o.amount_left:.2f} RUB\n"
                f"\tmin_op_threshold: {o.min_op_threshold:.2f} RUB\n"
                f"\tlifetime_sec: {o.lifetime_sec//3600} hours"
            )

        if self._admin_contacts:
            lines = ["match!"]
            for attr, value in vars(m).items():
                value_s = (
                    render_order(value)
                    if attr in ["sell_order", "buy_order"]
                    else value
                )
                lines.append(f"{attr}:\n{value_s}")
            message_for_admins = "\n\n".join(lines)

            for uid in self._admin_contacts:
                self._tg.send_message(TgOutgoingMsg(uid, None, message_for_admins))
