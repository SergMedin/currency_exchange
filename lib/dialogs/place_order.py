from typing import Any, Optional
from dataclasses import dataclass
from decimal import Decimal
import decimal
import logging
import unittest
from ..botlib.stories import (
    Controller,
    Event,
    OutMessage,
    Button,
    Message,
    ButtonAction,
)
from lib.data import User, OrderType, Order
from ..config import ORDER_LIFETIME_LIMIT
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
            text="Выберите тип заявки: покупка или продажа рублей",
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


def _str2dec(s: str) -> Decimal:
    return Decimal(s.replace(",", "."))


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
                amount = _str2dec(e.text)
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
            text="Введите курс или выберите опцию 'Относительный курс' чтобы ввести относительный курс. Относительный курс - это курс относительно курса биржи. Курс биржи обновляется раз в сутки.",
            buttons=[
                [Button("Относительный курс", "relative")],
                [Button("Отмена", "cancel")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Message):
            try:
                price = _str2dec(e.text)
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
                rate = _str2dec(e.text)
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
                min_op_threshold = _str2dec(e.text)
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

    def __init__(self, parent: "ConfirmOrderStep"):
        super().__init__(
            parent=parent,
            text="Укажите время жизни заявки в часах",
            buttons=[
                [
                    Button("12ч", "preset:12"),
                    Button("24ч", "preset:24"),
                    Button("3дн", "preset:72"),
                    Button("7дн", "preset:168"),
                ],
                [Button("Назад", "back")],
            ],
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
                assert isinstance(self.parent, ConfirmOrderStep)
                self.parent.order.lifetime_sec = lifetime_sec
                return self.close()
            except ValueError as e:
                return (
                    OutMessage("Время жизни заявки должно быть задано целым числом")
                    + self.render()
                )
        elif isinstance(e, ButtonAction):
            if e.name.startswith("preset:"):
                lifetime_sec = int(e.name.split(":")[1]) * 3600
                assert isinstance(self.parent, ConfirmOrderStep)
                self.parent.order.lifetime_sec = lifetime_sec
                res = self.close()
            elif e.name == "back":
                res = self.close()
            else:
                logging.error(f"SetLifetimeStep: Unknown action: {e.name}")
                res = self.render()
            return self.edit_last(e, res)
        logging.error(f"SetLifetimeStep: Unknown event: {e}")
        return self.close()


def _seconds_to_human(seconds: int) -> str:
    hours = seconds // 3600
    days = hours // 24
    hours = hours % 24
    x = ([] if days <= 0 else [f"{days} д"]) + (
        [] if hours <= 0 and days > 0 else [f"{hours} ч"]
    )
    return ", ".join(x)


@dataclass
class ConfirmOrderStep(ExchgController):
    confirmed: bool = False

    def __init__(self, parent: "CreateOrder"):
        super().__init__(
            parent=parent,
            text="",
            buttons=[
                [Button("Всё ок, разместить заявку", "place_order")],
                [Button("Указать мин. сумму сделки", "set_min_op_threshold")],
                [Button("Задать время жизни", "set_lifetime")],
                [Button("Отмена", "cancel")],
            ],
        )

    @property
    def order(self) -> _OrderDraft:
        assert isinstance(self.parent, CreateOrder)
        return self.parent.order

    def render(self) -> OutMessage:
        assert isinstance(self.parent, CreateOrder)
        order = self.parent.order
        assert order.type is not None

        type_name_rus = {"BUY": "покупка", "SELL": "продажа"}.get(
            order.type.name, order.type.name
        )

        lines = []
        lines.append("*Подтвердите параметры заявки:*")
        lines.append(f"- Тип: {type_name_rus} рублей")
        lines.append(f"- Сумма: {order.amount} RUB")
        if order.price is not None:
            lines.append(f"- Курс: 1 RUB = {order.price} AMD")
        else:
            assert order.relative_rate is not None
            lines.append(f"- Относительный курс: {order.relative_rate - 1 :.2%}")
        min_op_threshold_s = (
            "любая" if order.min_op_threshold is None else str(order.min_op_threshold)
        )
        lines.append(f"- Мин. сумма сделки: {min_op_threshold_s}")
        human_lifetime_s = _seconds_to_human(
            order.lifetime_sec if order.lifetime_sec else ORDER_LIFETIME_LIMIT
        )
        lines.append(f"- Время жизни заявки: {human_lifetime_s}")
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
                res = self.show_child(SetMinOpThresholdStep(self, self.order))
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
                    ORDER_LIFETIME_LIMIT
                    if order.lifetime_sec is None
                    else order.lifetime_sec
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
                        f"Ошибка размещения заявки: {e}"
                    ) + self.show_child(ConfirmOrderStep(self))
                return (
                    OutMessage("✅ Поздравляем! Ваша заявка размещена 🎉✨")
                    + self.close()
                )
        logging.error(f"CreateOrder: Unknown child: {child}, {child.__class__}")
        return self.cancel()

    def cancel(self):
        return self.close()


class T(unittest.TestCase):
    def test_secs_to_human(self):
        self.assertEqual(_seconds_to_human(0), "0 ч")
        self.assertEqual(_seconds_to_human(1), "0 ч")
        self.assertEqual(_seconds_to_human(3599), "0 ч")
        self.assertEqual(_seconds_to_human(3600), "1 ч")
        self.assertEqual(_seconds_to_human(3600 * 24), "1 д")
        self.assertEqual(_seconds_to_human(3600 * 24 * 7), "7 д")
        self.assertEqual(_seconds_to_human(3600 * 24 * 7 + 3600), "7 д, 1 ч")
        self.assertEqual(_seconds_to_human(3600 * 24 * 7 + 3600 + 1), "7 д, 1 ч")
        self.assertEqual(_seconds_to_human(3600 * 24 * 7 + 3600 + 1), "7 д, 1 ч")
        self.assertEqual(_seconds_to_human(3600 * 24 * 7 + 3600 + 3599), "7 д, 1 ч")
        self.assertEqual(_seconds_to_human(3600 * 24 * 7 + 3600 + 3600), "7 д, 2 ч")

    def test_str2dec(self):
        self.assertEqual(_str2dec("1"), Decimal(1))
        self.assertEqual(_str2dec("1.0"), Decimal(1))
        self.assertEqual(_str2dec("1,0"), Decimal(1))
        self.assertEqual(_str2dec("2,1"), Decimal("2.1"))
        self.assertRaises(decimal.InvalidOperation, _str2dec, "1,0,0")
