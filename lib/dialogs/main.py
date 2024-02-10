from typing import Any, Optional
from dataclasses import dataclass
from decimal import Decimal
import decimal
import os
import logging
from bootshop.stories import (
    Controller,
    Event,
    OutMessage,
    Button,
    Message,
    Command,
    ButtonAction,
)
from lib.lazy_load import LazyMessageLoader
from lib.data import User, OrderType, Order
from .session import Session
from .base import ExchgController
from .place_order import CreateOrder

_help_message_loader = LazyMessageLoader(
    os.path.join(os.path.dirname(__file__), "tg_messages", "help_message.md")
)

_start_message_loader = LazyMessageLoader(
    os.path.join(os.path.dirname(__file__), "tg_messages", "start_message.md")
)


class Main(ExchgController):
    def __init__(self, session: Session):
        tg_start_message = _start_message_loader.message
        super().__init__(
            text=tg_start_message,
            parse_mode="Markdown",
            buttons=[
                [
                    Button("Создать заказ", "create_order"),
                    Button("Мои заявки", "my_orders"),
                ],
                [Button("Статистика", "statistics"), Button("Помощь", "help")],
            ],
            _session=session,
        )
        self._a2c = {
            "create_order": CreateOrder,
            "my_orders": MyOrders,
            "statistics": Statistics,
            "help": Help,
        }

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Command):
            if e.name == "start":
                # return self.render()
                return (
                    OutMessage(
                        "Добро пожаловать в сервис обмена валюты!", buttons_below=[]
                    )
                    + self.render()
                )
            elif e.name == "help":
                return self.show_child(Help(self))
            else:
                raise ValueError(f"Invalid command: /{e.name}")
        elif isinstance(e, Message):
            if e.text.lower() == "help":
                return self.show_child(Help(self))
            return OutMessage(f"Неизвестная команда: {e.text}") + self.render()
        elif isinstance(e, ButtonAction):
            name = e.name.lower()
            try:
                child = self._a2c[name](self)
            except KeyError:
                return OutMessage(f"Неизвестная команда: {e.name}") + self.render()
            return self.show_child(child)
        raise NotImplementedError()


class MyOrders(ExchgController):
    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Мои заявки",
            buttons=[[Button("Back")]],
        )

    def render(self) -> OutMessage:
        m = super().render()
        # FIXME: I don't like that the controller knows about the exchange
        orders = self.session.exchange.list_orders_for_user(
            User(self.session.user_id, self.session.user_name)
        )
        if not orders:
            text = "У вас нет активных заявок"
        else:
            text = "Ваши заявки:\n"
            for o in orders:
                if o.relative_rate == -1.0:
                    text_about_rate = f"{o.price} AMD"
                else:
                    text_about_rate = f"{o.relative_rate} Относительный курс (текущее значение: {o.price} AMD)"

                text += (
                    "\n"
                    f"\tid: {o._id} ({o.type.name} {o.amount_left} RUB * {text_about_rate} "
                    f"минимальный объем {o.min_op_threshold} время жизни {o.lifetime_sec // 3600} "
                    f"[активно до: {self._convert_to_utc(o.creation_time, o.lifetime_sec)}])"
                )

            text += "\n\nчтобы удалить заявку, используйте команду /remove <id>"
        m.text = text
        return m

    @staticmethod
    def _convert_to_utc(creation_time, lifetime_sec):
        import datetime  # FIXME: the uglier the better

        # FIXME: refactor this out

        return datetime.datetime.fromtimestamp(
            creation_time + lifetime_sec, datetime.UTC
        )

    def process_event(self, e: Event) -> OutMessage:
        return self.close()


class Statistics(ExchgController):
    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="",
            buttons=[[Button("Назад", "back")]],
        )

    def render(self) -> OutMessage:
        m = super().render()
        # FIXME: should go somewhere in application
        ex = self.session.exchange
        ex._check_order_lifetime()  # FIXME: should be removed
        text = ex.get_stats()["text"]
        m.text = text
        return m

    def process_event(self, e: Event) -> OutMessage:
        # if isinstance(e, ButtonAction):
        # return self.close()
        # raise NotImplementedError()
        return self.close()


class Help(Controller):
    def __init__(self, parent: Controller):
        text = _help_message_loader.message
        super().__init__(
            parent=parent,
            text=text,
            parse_mode="Markdown",
            buttons=[[Button("Назад", "back")]],
        )

    def process_event(self, e: Event) -> OutMessage:
        logging.info(f"Help.process_event: {e}")
        return self.close()
