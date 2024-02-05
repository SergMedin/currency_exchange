from typing import Any, Optional
from dataclasses import dataclass
from decimal import Decimal
import decimal
import logging
from bootshop.stories import (
    Controller,
    Event,
    OutMessage,
    Button,
    Message,
    ButtonAction,
)
from lib.data import User, OrderType, Order
from .base import ExchgController


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
                [Button("RUB ➡️ AMD", "rub_amd"), Button("AMD ➡️ RUB", "amd_rub")],
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
                return self.close()
        return self.render()


@dataclass
class EnterRelativeRateStep(ExchgController):

    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Укажите, сколько % прибавть к текущему курсу биржи",
            buttons=[
                [Button("Использовать курс биржи", "rel:0")],
                [
                    Button("-2.0%", "rel:-2"),
                    Button("-1.5%", "rel:-1.5"),
                    Button("-1.0%", "rel:-1"),
                    Button("-0.5%", "rel:-0.5"),
                ],
                [
                    Button("+0.5%", "rel:0.5"),
                    Button("+1.0%", "rel:1"),
                    Button("+1.5%", "rel:1.5"),
                    Button("+2.0%", "rel:2"),
                ],
                [Button("Назад", "back")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                rate = Decimal(e.text)
                if rate <= 0:
                    return OutMessage("Rate have to be > 0") + self.render()
                assert self.parent is not None
                assert isinstance(self.parent, EnterPriceStep)
                self.parent.relative_rate = rate / Decimal(100) + Decimal(1)
                return self.close()
            except decimal.InvalidOperation as e:
                return (
                    OutMessage("Rate should be a valid decimal number") + self.render()
                )
        elif isinstance(e, ButtonAction):
            if e.name == "back":
                return self.close()
            elif e.name.startswith("rel:"):
                rate = Decimal(e.name.split(":")[1]) / Decimal(100) + Decimal(1)
                assert self.parent is not None
                assert isinstance(self.parent, EnterPriceStep)
                self.parent.relative_rate = rate
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
                [Button("Указать мин. сумму сделки", "set_min_op_threshold")],
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
                assert order.price is not None or order.relative_rate is not None
                if order.price is None:
                    order.price = Decimal(
                        1
                    )  # FIXME: workaround broken exchange interface
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
                return OutMessage("Поздравляем! Ваш заказ размещен") + self.close()
        logging.error(f"Unknown child: {child}, {child.__class__}")
        raise NotImplementedError()

    def cancel(self):
        return self.close()
