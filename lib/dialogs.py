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
from .lazy_load import LazyMessageLoader
from .exchange import Exchange
from .data import User, OrderType, Order


_help_message_loader = LazyMessageLoader(
    os.path.join(os.path.dirname(__file__), "tg_messages", "help_message.md")
)


# FIXME: should go to the framework level
@dataclass
class Session:
    user_id: int
    user_name: str
    exchange: Exchange


@dataclass
class ExchgController(Controller):
    _session: Session | None = None  # FIXME: this is ugly. Should be refactored

    @property
    def session(self) -> Session:
        # FIXME: this is ugly. Should be refactored
        if self._session is None:
            assert self.parent is not None
            assert isinstance(self.parent, ExchgController)
            return self.parent.session
        return self._session


class Main(ExchgController):
    def __init__(self, session: Session):
        with open("./lib/tg_messages/start_message.md", "r") as f:
            tg_start_message = f.read().strip()
        super().__init__(
            text=tg_start_message,
            parse_mode="Markdown",
            buttons=[
                [
                    Button("Создать заказ", "create_order"),
                    Button("My orders", "my_orders"),
                ],
                [Button("Statistics", "statistics"), Button("Help", "help")],
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
                return self.render()
            elif e.name == "help":
                return self.show_child(Help(self))
            else:
                raise ValueError(f"Invalid command: /{e.name}")
        elif isinstance(e, Message):
            if e.text.lower() == "help":
                return self.show_child(Help(self))
            raise ValueError(f"Unknown message: {e.text}")
        elif isinstance(e, ButtonAction):
            return self.show_child(self._a2c[e.name.lower()](self))
        raise NotImplementedError()


@dataclass
class _OrderDraft:
    type: Optional[OrderType] = None
    amount: Optional[Decimal] = None
    price: Optional[Decimal] = None
    min_op_threshold: Optional[Decimal] = None
    lifetime_sec: Optional[int] = None
    relative_rate: Optional[Decimal] = None


@dataclass
class ChooseOrderTypeStep(ExchgController):
    order_type: OrderType | None = None

    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Choose the type of order",
            buttons=[
                [Button("RUB -> AMD", "rub_amd"), Button("AMD -> RUB", "amd_rub")],
                [Button("Cancel", "cancel")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            if e.name == "cancel":
                assert self.parent is not None and isinstance(self.parent, CreateOrder)
                return self.parent.cancel()
            self.order_type = OrderType.BUY if e.name == "rub_amd" else OrderType.SELL
            return self.close()
        raise NotImplementedError()


@dataclass
class EnterAmountStep(ExchgController):
    amount: Decimal | None = None

    def __init__(self, parent: Controller, order_type: OrderType):
        text = (
            "How much RUB do you want to exchange?"
            if order_type == OrderType.BUY
            else "How much AMD do you want to exchange?"
        )
        super().__init__(
            parent=parent,
            text=text,
            buttons=[[Button("Cancel", "cancel")]],
        )
        self.order_type = order_type

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                amount = Decimal(e.text)
                if amount <= 0:
                    return OutMessage("Amount have to be > 0") + self.render()
                assert self.parent is not None
                assert isinstance(self.parent, CreateOrder)
                self.amount = amount
                return self.close()
            except decimal.InvalidOperation as e:
                return (
                    OutMessage("Amount should be a valid decimal number")
                    + self.render()
                )
        elif isinstance(e, ButtonAction):
            if e.name == "cancel":
                assert self.parent is not None and isinstance(self.parent, CreateOrder)
                return self.parent.cancel()
        raise NotImplementedError()


@dataclass
class EnterPriceStep(ExchgController):
    price: Decimal | None = None
    relative_rate: Decimal | None = None

    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Введите курс или выберите опцию 'Относительный курс' чтобы ввести относительный курс",
            buttons=[
                [Button("Относительный курс", "relative")],
                [Button("Cancel", "cancel")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                price = Decimal(e.text)
                if price <= 0:
                    return OutMessage("Price have to be > 0") + self.render()
                assert self.parent is not None
                assert isinstance(self.parent, CreateOrder)
                self.price = price
                return self.close()
            except decimal.InvalidOperation as e:
                return (
                    OutMessage("Price should be a valid decimal number") + self.render()
                )
        elif isinstance(e, ButtonAction):
            if e.name == "cancel":
                assert self.parent is not None and isinstance(self.parent, CreateOrder)
                return self.parent.cancel()
            elif e.name == "relative":
                return self.show_child(EnterRelativeRateStep(self))
        raise NotImplementedError()

    def on_child_closed(self, child: Controller) -> OutMessage:
        if isinstance(child, EnterRelativeRateStep):
            if self.relative_rate:
                self.close()
        return self.render()


@dataclass
class EnterRelativeRateStep(ExchgController):

    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Enter the desired exchange rate relative to the exchange. For example: 1.01 (above the exchange rate by 1%) or 0.98 (below the exchange rate by 2%). Current exchange rate: 4.4628 AMD/RUB",
            buttons=[[Button("Назад", "back")]],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                rate = Decimal(e.text)
                if rate <= 0:
                    return OutMessage("Rate have to be > 0") + self.render()
                assert self.parent is not None
                assert isinstance(self.parent, EnterPriceStep)
                self.parent.relative_rate = rate
                return self.close()
            except decimal.InvalidOperation as e:
                return (
                    OutMessage("Rate should be a valid decimal number") + self.render()
                )
        elif isinstance(e, ButtonAction):
            if e.name == "back":
                return self.close()
        raise NotImplementedError()


class SetMinOpThresholdStep(ExchgController):

    def __init__(self, parent: Controller):
        assert parent is not None and isinstance(parent, ConfirmOrderStep)
        super().__init__(
            parent=parent,
            text="Укажите минимальную сумму для операции",
            buttons=[[Button("Назад", "back")]],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                min_op_threshold = Decimal(e.text)
                if min_op_threshold <= 0:
                    return OutMessage("Min op threshold have to be > 0") + self.render()
                assert self.parent is not None and isinstance(
                    self.parent, ConfirmOrderStep
                )
                self.parent.min_op_threshold = min_op_threshold
                return self.close()
            except decimal.InvalidOperation as e:
                return (
                    OutMessage("Min op threshold should be a valid decimal number")
                    + self.render()
                )
        elif isinstance(e, ButtonAction):
            if e.name == "back":
                return self.close()
        raise NotImplementedError()


class SetLifetimeStep(ExchgController):

    def __init__(self, parent: Controller):
        assert parent is not None and isinstance(parent, ConfirmOrderStep)
        super().__init__(
            parent=parent,
            text="Укажите время жизни заказа в часах",
            buttons=[[Button("Назад", "back")]],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                lifetime_sec = int(e.text) * 3600
                if lifetime_sec <= 0:
                    return OutMessage("Lifetime have to be > 0") + self.render()
                assert self.parent is not None and isinstance(
                    self.parent, ConfirmOrderStep
                )
                self.parent.lifetime_sec = lifetime_sec
                return self.close()
            except ValueError as e:
                return (
                    OutMessage("Lifetime should be a valid integer number")
                    + self.render()
                )
        elif isinstance(e, ButtonAction):
            if e.name == "back":
                return self.close()
        raise NotImplementedError()


@dataclass
class ConfirmOrderStep(ExchgController):
    confirmed: bool = False
    min_op_threshold: Decimal | None = None
    lifetime_sec: int | None = None

    def __init__(self, parent: Controller):
        assert parent is not None and isinstance(parent, CreateOrder)
        super().__init__(
            parent=parent,
            text=f"Подтвердите параметры заказа: {parent.order.type} {parent.order.amount} RUB * {parent.order.price} AMD",
            buttons=[
                [Button("Всё ок, разместить заказ", "place_order")],
                [Button("Указать мин. сумму", "set_min_op_threshold")],
                [Button("Задать время жизни", "set_lifetime")],
                [Button("Cancel", "cancel")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            if e.name == "cancel":
                assert self.parent is not None and isinstance(self.parent, CreateOrder)
                return self.parent.cancel()
            elif e.name == "place_order":
                self.confirmed = True
                return self.close()
            elif e.name == "set_min_op_threshold":
                return self.show_child(SetMinOpThresholdStep(self))
            elif e.name == "set_lifetime":
                return self.show_child(SetLifetimeStep(self))
        raise NotImplementedError()


class CreateOrder(ExchgController):

    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Not supported yet",
            buttons=[
                [Button("Back")],
            ],
        )
        self.order = _OrderDraft()
        self.child = ChooseOrderTypeStep(self)

    def on_child_closed(self, child: Controller) -> OutMessage:
        if isinstance(child, ChooseOrderTypeStep):
            if child.order_type is not None:
                self.order.type = child.order_type
                return self.show_child(EnterAmountStep(self, child.order_type))
        elif isinstance(child, EnterAmountStep):
            if child.amount is not None:
                self.order.amount = child.amount
                return self.show_child(EnterPriceStep(self))
        elif isinstance(child, EnterPriceStep):
            if child.price is not None or child.relative_rate is not None:
                self.order.price = child.price
                self.order.relative_rate = child.relative_rate
                return self.show_child(ConfirmOrderStep(self))
        elif isinstance(child, ConfirmOrderStep):
            if child.confirmed:
                order = self.order
                assert order.type is not None
                assert order.amount is not None
                assert order.price is not None
                order.min_op_threshold = (
                    order.amount
                    if child.min_op_threshold is None
                    else child.min_op_threshold
                )
                order.lifetime_sec = (
                    48 * 60 * 60 if child.lifetime_sec is None else child.lifetime_sec
                )
                if order.relative_rate is None:
                    order.relative_rate = Decimal(-1.0)

                o: Order = Order(
                    user=User(self.session.user_id, self.session.user_name),
                    type=order.type,
                    amount_initial=order.amount,
                    price=order.price,
                    min_op_threshold=order.min_op_threshold,
                    lifetime_sec=order.lifetime_sec,
                    relative_rate=order.relative_rate,
                )
                self.session.exchange.on_new_order(o)
                return self.close()
        logging.error(f"Unknown child: {child}, {child.__class__}")
        raise NotImplementedError()

    def cancel(self):
        return self.close()


class MyOrders(ExchgController):
    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="My orders",
            buttons=[[Button("Back")]],
        )

    def render(self) -> OutMessage:
        m = super().render()
        # FIXME: I don't like that the controller knows about the exchange
        orders = self.session.exchange.list_orders_for_user(
            User(self.session.user_id, self.session.user_name)
        )
        if not orders:
            text = "You don't have any active orders"
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
            buttons=[[Button("Back")]],
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
        if isinstance(e, ButtonAction):
            return self.close()
        raise NotImplementedError()


class Help(Controller):
    def __init__(self, parent: Controller):
        text = _help_message_loader.message
        super().__init__(
            parent=parent,
            text=text,
            parse_mode="Markdown",
            buttons=[[Button("Back", "back")]],
        )

    def process_event(self, e: Event) -> OutMessage:
        logging.info(f"Help.process_event: {e}")
        return self.close()
