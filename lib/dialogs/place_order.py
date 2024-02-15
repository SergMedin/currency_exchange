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
            text="Выберите тип заказа: покупка или продажа рублей",
            buttons=[
                [
                    Button("Продать RUB → AMD", "rub_amd"),
                    Button("Купить RUB ← AMD", "amd_rub"),
                ],
                [Button("Отмена", "cancel")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        res: OutMessage
        if isinstance(e, ButtonAction):
            if e.name == "cancel":
                assert self.parent is not None and isinstance(self.parent, CreateOrder)
                res = self.parent.cancel()
            elif e.name in ("rub_amd", "amd_rub"):
                self.order_type = (
                    OrderType.BUY if e.name == "amd_rub" else OrderType.SELL
                )
                res = self.close()
            else:
                res = self.render()
            res = self.edit_last(e, res)
        else:
            res = self.render()
        return res


@dataclass
class EnterAmountStep(ExchgController):
    amount: Decimal | None = None

    def __init__(self, parent: Controller, order_type: OrderType):
        text = (
            "Сколько рублей продаете?"
            if order_type == OrderType.SELL
            else "Сколько рублей хотите купить?"
        )
        super().__init__(
            parent=parent,
            text=text,
        )
        self.order_type = order_type

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                amount = Decimal(e.text)
                if amount <= 0:
                    return OutMessage("Сумма должна быть более 0") + self.render()
                assert self.parent is not None
                assert isinstance(self.parent, CreateOrder)
                self.amount = amount
                return self.close()
            except decimal.InvalidOperation as e:
                return OutMessage("Сумма должна быть задана числом") + self.render()
        return self.render()


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
                [Button("Отмена", "cancel")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                price = Decimal(e.text)
                if price <= 0:
                    return (
                        OutMessage("Курс обмена должен быть больше 0") + self.render()
                    )
                assert self.parent is not None
                assert isinstance(self.parent, CreateOrder)
                self.price = price
                return self.close()
            except decimal.InvalidOperation as e:
                return OutMessage("Курс обмена должен быть числом") + self.render()
        elif isinstance(e, ButtonAction):
            res: OutMessage
            if e.name == "cancel":
                assert self.parent is not None and isinstance(self.parent, CreateOrder)
                res = self.parent.cancel()
            elif e.name == "relative":
                res = self.show_child(EnterRelativeRateStep(self))
            else:
                logging.error(f"EnterPriceStep: Unknown action: {e.name}")
                res = self.render()
            return self.edit_last(e, res)
        return self.render()

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
            text="Укажите относительный курс биржи в процентах",
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
                assert self.parent is not None
                assert isinstance(self.parent, EnterPriceStep)
                self.parent.relative_rate = rate / Decimal(100) + Decimal(1)
                return self.close()
            except decimal.InvalidOperation as e:
                return (
                    OutMessage("Процент должен быть задан числом, например 1.5")
                    + self.render()
                )
        elif isinstance(e, ButtonAction):
            res: OutMessage
            if e.name == "back":
                res = self.close()
            elif e.name.startswith("rel:"):
                rate = Decimal(e.name.split(":")[1]) / Decimal(100) + Decimal(1)
                assert self.parent is not None
                assert isinstance(self.parent, EnterPriceStep)
                self.parent.relative_rate = rate
                res = self.close()
            else:
                logging.error(f"EnterRelativeRateStep: Unknown action: {e.name}")
                res = self.render()
            return self.edit_last(e, res)
        logging.error(f"EnterRelativeRateStep: Unknown event: {e}")
        return self.render()


class SetMinOpThresholdStep(ExchgController):

    def __init__(self, parent: Controller, draft: _OrderDraft):
        self._draft = draft
        super().__init__(
            parent=parent,
            text=f"Укажите минимальную сумму для операции <= {draft.amount} RUB",
            buttons=[
                [Button("Вся сумма", "all-in")],
                [Button("Назад", "back")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                min_op_threshold = Decimal(e.text)
                if min_op_threshold <= 0:
                    return (
                        OutMessage("Размер минимальной транзакции должен быть больше 0")
                        + self.render()
                    )
                self._draft.min_op_threshold = min_op_threshold
                return self.close()
            except decimal.InvalidOperation as e:
                return (
                    OutMessage("Размер минимальной транзакции должен быть задан числом")
                    + self.render()
                )
        elif isinstance(e, ButtonAction):
            res: OutMessage
            if e.name == "back":
                res = self.close()
            elif e.name == "all-in":
                self._draft.min_op_threshold = self._draft.amount
                res = self.close()
            else:
                logging.error(f"SetMinOpThresholdStep: Unknown action: {e.name}")
                res = self.render()
            return self.edit_last(e, res)
        logging.error(f"SetMinOpThresholdStep: Unknown event: {e}")
        return self.render()


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
                    return (
                        OutMessage("Время жизни заявки должно быть больше 0")
                        + self.render()
                    )
                assert self.parent is not None and isinstance(
                    self.parent, ConfirmOrderStep
                )
                self.parent.lifetime_sec = lifetime_sec
                return self.close()
            except ValueError as e:
                return (
                    OutMessage("Время жизни заявки должно быть задано целым числом")
                    + self.render()
                )
        elif isinstance(e, ButtonAction):
            if e.name == "back":
                return self.close()
        return self.close()


@dataclass
class ConfirmOrderStep(ExchgController):
    confirmed: bool = False
    lifetime_sec: int | None = None

    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="",
            buttons=[
                [Button("Всё ок, разместить заказ", "place_order")],
                [Button("Указать мин. сумму сделки", "set_min_op_threshold")],
                # [Button("Задать время жизни", "set_lifetime")],
                [Button("Отмена", "cancel")],
            ],
        )

    def render(self) -> OutMessage:
        parent = self.parent
        assert parent is not None and isinstance(parent, CreateOrder)
        assert parent.order.type is not None

        type_name_rus = {"BUY": "покупка", "SELL": "продажа"}.get(
            parent.order.type.name, parent.order.type.name
        )

        lines = []
        lines.append("*Подтвердите параметры заказа:*")
        lines.append(f"- Тип: {type_name_rus} рублей")
        lines.append(f"- Сумма: {parent.order.amount} RUB")
        if parent.order.price is not None:
            lines.append(f"- Курс: 1 RUB = {parent.order.price} AMD")
        else:
            assert parent.order.relative_rate is not None
            lines.append(f"- Относительный курс: {parent.order.relative_rate - 1 :.2%}")
        lines.append(
            f"- Мин. сумма сделки: любая"
            if parent.order.min_op_threshold is None
            else f"- Мин. сумма сделки: {parent.order.min_op_threshold}"
        )
        lines.append(
            f"- Время жизни заявки: {parent.order.lifetime_sec // 3600} часов"
            if parent.order.lifetime_sec is not None
            else "- Время жизни заявки: 30 суток"  # FIXME: hardcoded value
        )
        m = super().render()
        m.text = "\n".join(lines)
        m.parse_mode = "Markdown"
        return m

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            res: OutMessage
            if e.name == "cancel":
                assert self.parent is not None and isinstance(self.parent, CreateOrder)
                res = self.parent.cancel()
            elif e.name == "place_order":
                self.confirmed = True
                res = self.close()
            elif e.name == "set_min_op_threshold":
                assert self.parent is not None and isinstance(self.parent, CreateOrder)
                res = self.show_child(SetMinOpThresholdStep(self, self.parent.order))
            elif e.name == "set_lifetime":
                res = self.show_child(SetLifetimeStep(self))
            else:
                logging.error(f"ConfirmOrderStep: Unknown action: {e.name}")
                res = self.render()
            return self.edit_last(e, res)
        logging.error(f"ConfirmOrderStep: Unknown event: {e}")
        return self.render()


class CreateOrder(ExchgController):

    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Не поддерживается",
            buttons=[
                [Button("Назад", "back")],
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
                try:  # FIXME
                    assert order.type is not None
                    assert order.amount is not None
                    assert order.price is not None or order.relative_rate is not None
                    if order.price is None:
                        order.price = Decimal(
                            1
                        )  # FIXME: workaround broken exchange interface
                    assert (
                        order.min_op_threshold is None
                        or order.min_op_threshold <= order.amount
                    )
                except AssertionError as e:
                    return OutMessage(f"{e}") + self.show_child(ConfirmOrderStep(self))
                order.lifetime_sec = (
                    30 * 24 * 60 * 60
                    if child.lifetime_sec is None
                    else child.lifetime_sec  # Fixme: hardcoded value
                )
                if order.relative_rate is None:
                    order.relative_rate = Decimal(-1.0)

                o: Order = Order(
                    user=User(self.session.user_id, self.session.user_name),
                    type=order.type,
                    amount_initial=order.amount,
                    price=order.price,
                    min_op_threshold=(
                        order.min_op_threshold
                        if order.min_op_threshold
                        else Decimal(0.0)
                    ),
                    lifetime_sec=order.lifetime_sec,
                    relative_rate=order.relative_rate,
                )
                try:  # FIXME
                    self.session.exchange.place_order(o)
                except Exception as e:
                    logging.exception("CreateOrder: Error placing order")
                    return OutMessage(
                        f"Ошибка размещения заказа: {e}"
                    ) + self.show_child(ConfirmOrderStep(self))
                return OutMessage("Поздравляем! Ваш заказ размещен") + self.close()
        logging.error(f"CreateOrder: Unknown child: {child}, {child.__class__}")
        return self.cancel()

    def cancel(self):
        return self.close()
