from decimal import Decimal
from typing import Optional
import unittest
import os
from unittest.mock import patch

from ..application import Application
from ..botlib.tg import TelegramMock
from ..currency_rates import CurrencyMockClient
from ..db_sqla import SqlDb


class TestOrderCreationDialogs(unittest.TestCase):
    def setUp(self):
        self.tg = TelegramMock()
        self.db = SqlDb()
        self.app = Application(self.db, self.tg, currency_client=CurrencyMockClient())

    def test_simple_path(self):
        self._create_order()

    def _create_order(
        self,
        stop_on_type=False,
        stop_on_amount=False,
        stop_on_rate=False,
        stop_on_confirm=False,
        set_lifetime_to: Optional[int] = None,
        set_min_op_threshold_to: Optional[Decimal | str] = None,
        stop_on_lifetime=False,
        order_amount: Decimal | str = "1111",
        order_rate: Decimal | str = "4.5",
    ):
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="create_order")
        self.assertIn("Выберите тип заказа", self.tg.outgoing[-1].text)
        if stop_on_type:
            return
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="rub_amd")
        self.assertIn("Сколько рублей продаете?", self.tg.outgoing[-1].text)
        if stop_on_amount:
            return
        self.tg.emulate_incoming_message(1, "Joe", order_amount)
        self.assertIn("Введите курс", self.tg.outgoing[-1].text)
        if stop_on_rate:
            return
        self.tg.emulate_incoming_message(1, "Joe", order_rate)
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)
        if set_lifetime_to is not None:
            self.tg.emulate_incoming_message(
                1, "Joe", "", keyboard_callback="set_lifetime"
            )
            self.assertIn(
                "Укажите время жизни заказа в часах", self.tg.outgoing[-1].text
            )
            if stop_on_lifetime:
                return
            self.tg.emulate_incoming_message(1, "Joe", str(set_lifetime_to))
            self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)
        if set_min_op_threshold_to is not None:
            self.tg.emulate_incoming_message(
                1, "Joe", "", keyboard_callback="set_min_op_threshold"
            )
            self.assertIn(
                "Укажите минимальную сумму для операции", self.tg.outgoing[-1].text
            )
            self.tg.emulate_incoming_message(1, "Joe", str(set_min_op_threshold_to))
            self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)
        if stop_on_confirm:
            return
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="place_order")
        self.assertIn("Поздравляем! Ваш заказ размещен", self.tg.outgoing[-2].text)


class TestLifetimeStep(TestOrderCreationDialogs):
    def test_lifetime_simple(self):
        self._create_order(set_lifetime_to=1, stop_on_confirm=True)
        self.assertIn("Время жизни заявки: 1 ч", self.tg.outgoing[-1].text)

    def _create_order_with_lifetime(self, lifetime: int, check_for: str):
        self._create_order(set_lifetime_to=1, stop_on_lifetime=True)
        self.tg.emulate_incoming_message(
            1, "Joe", "", keyboard_callback=f"preset:{lifetime}"
        )
        self.assertIn(f"Время жизни заявки: {check_for}", self.tg.outgoing[-1].text)

    def test_lifetime_button_12h(self):
        self._create_order_with_lifetime(12, "12 ч")

    def test_lifetime_button_24h(self):
        self._create_order_with_lifetime(24, "1 д")

    def test_lifetime_button_3d(self):
        self._create_order_with_lifetime(72, "3 д")

    def test_lifetime_button_7d(self):
        self._create_order_with_lifetime(168, "7 д")

    def test_lifetime_button_back(self):
        self._create_order(set_lifetime_to=1, stop_on_lifetime=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)

    @patch("logging.error")
    def test_lifetime_bad_button(self, _):
        self._create_order(set_lifetime_to=1, stop_on_lifetime=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="bad_button")
        self.assertIn("Укажите время жизни заказа в часах", self.tg.outgoing[-1].text)

    def test_lifetime_negative(self):
        self._create_order(set_lifetime_to=1, stop_on_lifetime=True)
        self.tg.emulate_incoming_message(1, "Joe", "-1")
        self.assertIn("должно быть больше 0", self.tg.outgoing[-2].text)

    def test_lifetime_invalid_number(self):
        self._create_order(set_lifetime_to=1, stop_on_lifetime=True)
        self.tg.emulate_incoming_message(1, "Joe", "abc")
        self.assertIn("должно быть задано целым числом", self.tg.outgoing[-2].text)


class TestMinOpThresholdSetop(TestOrderCreationDialogs):
    def test_not_specified(self):
        self._create_order(stop_on_confirm=True)
        self.assertIn("сумма сделки: любая", self.tg.outgoing[-1].text)

    def test_enter_manually(self):
        self._create_order(set_min_op_threshold_to=1000, stop_on_confirm=True)
        self.assertIn("сумма сделки: 1000\n", self.tg.outgoing[-1].text)


class TestInputNumbersFormatHandling(TestOrderCreationDialogs):
    def test_dots(self):
        self._create_order(
            order_amount="555.1",
            order_rate="4.5",
            set_min_op_threshold_to="400,1",
            stop_on_confirm=True,
        )
        self.assertIn("555.1", self.tg.outgoing[-1].text)
        self.assertIn("4.5", self.tg.outgoing[-1].text)
        self.assertIn("400.1", self.tg.outgoing[-1].text)

    def test_commas(self):
        self._create_order(
            order_amount="555,1",
            order_rate="4,5",
            set_min_op_threshold_to="400,1",
            stop_on_confirm=True,
        )
        self.assertIn("555.1", self.tg.outgoing[-1].text)
        self.assertIn("4.5", self.tg.outgoing[-1].text)
        self.assertIn("400.1", self.tg.outgoing[-1].text)
