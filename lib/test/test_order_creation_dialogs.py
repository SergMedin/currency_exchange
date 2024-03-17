from decimal import Decimal
from typing import Optional
from unittest.mock import patch

from .base import ExchgTestBase


class TestOrderCreationDialogs(ExchgTestBase):

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
            set_min_op_threshold_to="400.1",
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


class TestCreateOrder(TestOrderCreationDialogs):
    def test_simple(self):
        self._create_order(stop_on_type=True)
        self.assertIn("Выберите тип заказа", self.tg.outgoing[-1].text)

    def test_cancel(self):
        self._create_order(stop_on_type=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="cancel")
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)

    def test_text(self):
        self._create_order(stop_on_type=True)
        self.tg.emulate_incoming_message(1, "Joe", "random text")
        self.assertIn("Выберите тип заказа", self.tg.outgoing[-1].text)

class TestChooseOrderTypeStep(TestOrderCreationDialogs):
    def test_choose_rub_amd(self):
        self._create_order(stop_on_type=True)
        self.assertIn("Выберите тип заказа", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="rub_amd")
        self.assertIn("Сколько рублей продаете?", self.tg.outgoing[-1].text)

    def test_choose_amd_rub(self):
        self._create_order(stop_on_type=True)
        self.assertIn("Выберите тип заказа", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="amd_rub")
        self.assertIn("Сколько рублей хотите купить?", self.tg.outgoing[-1].text)

    def test_enter_random_text(self):
        self._create_order(stop_on_type=True)
        self.assertIn("Выберите тип заказа", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "random text")
        self.assertIn("Выберите тип заказа", self.tg.outgoing[-1].text)
    
    def test_cancel(self):
        self._create_order(stop_on_type=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="cancel")
        self.assertIn("Выберите действие:", self.tg.outgoing[-1].text)

class TestEnterAmountStep(TestOrderCreationDialogs):
    def test_simple(self):
        self._create_order(stop_on_amount=True)
        self.assertIn("Сколько рублей продаете?", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "1000")
        self.assertIn("Введите курс", self.tg.outgoing[-1].text)

    def test_negative_value(self):
        self._create_order(stop_on_amount=True)
        self.assertIn("Сколько рублей продаете?", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "-1")
        self.assertIn("Сумма должна быть более 0", self.tg.outgoing[-2].text)

    def test_zero_value(self):
        self._create_order(stop_on_amount=True)
        self.assertIn("Сколько рублей продаете?", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "0")
        self.assertIn("Сумма должна быть более 0", self.tg.outgoing[-2].text)
    
    def test_invalid_number(self):
        self._create_order(stop_on_amount=True)
        self.assertIn("Сколько рублей продаете?", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "abc")
        self.assertIn("Сумма должна быть задана числом", self.tg.outgoing[-2].text)

    def test_float_number_comma(self):
        self._create_order(stop_on_amount=True)
        self.assertIn("Сколько рублей продаете?", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "1,1")
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)

    def test_float_number_dot(self):
        self._create_order(stop_on_amount=True)
        self.assertIn("Сколько рублей продаете?", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "1.1")
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)


class TestEnterRateStep(TestOrderCreationDialogs):
    def test_simple(self):
        self._create_order(stop_on_rate=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="relative")
        self.assertIn("Укажите относительный курс", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "1")
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)

    def test_invalid_number(self):
        self._create_order(stop_on_rate=True)
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "abc")
        self.assertIn("Курс обмена должен быть числом", self.tg.outgoing[-2].text)

    def test_negative(self):
        self._create_order(stop_on_rate=True)
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "-1")
        self.assertIn("Курс обмена должен быть больше 0", self.tg.outgoing[-2].text)

    def test_zero(self):
        self._create_order(stop_on_rate=True)
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "0")
        self.assertIn("Курс обмена должен быть больше 0", self.tg.outgoing[-2].text)

    def _rel(self, rel: str, expected: str):
        self._create_order(stop_on_rate=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback=f"rel:{rel}")
        self.assertIn(expected, self.tg.outgoing[-1].text)

    def test_rel_minus_one(self):
        self._rel("-1", "Относительный курс: -1.00%")

    def test_rel_plus_one(self):
        self._rel("+1", "Относительный курс: 1.00%")

    def test_rel_exact(self):
        self._rel("+0", "Относительный курс: 0.00%")

    def test_cancel(self):
        self._create_order(stop_on_rate=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="cancel")
        self.assertIn("Выберите действие:", self.tg.outgoing[-1].text)

    def test_relative(self):
        self._create_order(stop_on_rate=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="relative")
        self.assertIn("Укажите относительный курс", self.tg.outgoing[-1].text)

    @patch("logging.error")
    def test_bad_button(self, x):
        self._create_order(stop_on_rate=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="bad_button")
        self.assertIn("Введите курс", self.tg.outgoing[-1].text)
        x.assert_called_once()
        x.assert_called_with("EnterPriceStep: Unknown action: bad_button")


class TestEnterRelativeRateStep(TestOrderCreationDialogs):
    def test_simple(self):
        self._create_order(stop_on_rate=True)
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="rel:0")
        self.assertIn("Подтвердите параметры заказа:", self.tg.outgoing[-1].text)

    def test_invalid_number(self):
        self._create_order(stop_on_rate=True)
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "abc")
        self.assertIn("Курс обмена должен быть числом", self.tg.outgoing[-2].text)

    def test_negative(self):
        self._create_order(stop_on_rate=True)
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "-1")
        self.assertIn("Курс обмена должен быть больше 0", self.tg.outgoing[-2].text)

    def test_zero(self):
        self._create_order(stop_on_rate=True)
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "0")
        self.assertIn("Курс обмена должен быть больше 0", self.tg.outgoing[-2].text)
    
    def test_cancel(self):
        self._create_order(stop_on_rate=True)
        self.assertIn("Введите курс обмена", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="cancel")
        self.assertIn("Выберите действие:", self.tg.outgoing[-1].text)

    def test_relative_details_float_dot(self):
        self._create_order(stop_on_rate=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="relative")
        self.assertIn("Укажите относительный курс", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "1.1")
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)

    def test_relative_details_float_comma(self):
        self._create_order(stop_on_rate=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="relative")
        self.assertIn("Укажите относительный курс", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "1,1")
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)
    
    def test_relative_details_invalid(self):
        self._create_order(stop_on_rate=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="relative")
        self.assertIn("Укажите относительный курс", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "abc")
        self.assertIn("Процент должен быть задан числом, например 1.5", self.tg.outgoing[-2].text)
    
    def test_relative_details_negative(self):
        self._create_order(stop_on_rate=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="relative")
        self.assertIn("Укажите относительный курс", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "-1")
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)


class TestSetMinOpThresholdStep(TestOrderCreationDialogs):
    def test_simple(self):
        self._create_order(stop_on_confirm=True, set_min_op_threshold_to="1000")
        self.assertIn("Мин. сумма сделки: 1000", self.tg.outgoing[-1].text)

    def test_invalid_number(self):
        self._create_order(stop_on_confirm=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="set_min_op_threshold")
        self.assertIn("Укажите минимальную сумму для операции", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "abc")
        self.assertIn("Размер минимальной транзакции должен быть задан числом", self.tg.outgoing[-2].text)

    def test_negative(self):
        self._create_order(stop_on_confirm=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="set_min_op_threshold")
        self.assertIn("Укажите минимальную сумму для операции", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "-1")
        self.assertIn("Размер минимальной транзакции должен быть больше 0", self.tg.outgoing[-2].text)

    def test_zero(self):
        self._create_order(stop_on_confirm=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="set_min_op_threshold")
        self.assertIn("Укажите минимальную сумму для операции", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "0")
        # FIXME: а может быть разрешить 0?
        self.assertIn("Размер минимальной транзакции должен быть больше 0", self.tg.outgoing[-2].text)

    def test_cancel(self):
        self._create_order(stop_on_confirm=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="set_min_op_threshold")
        self.assertIn("Укажите минимальную сумму для операции", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="cancel")
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)
    
    def test_float_number_comma(self):
        self._create_order(stop_on_confirm=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="set_min_op_threshold")
        self.assertIn("Укажите минимальную сумму для операции", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "1,1")
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)

    def test_float_number_dot(self):
        self._create_order(stop_on_confirm=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="set_min_op_threshold")
        self.assertIn("Укажите минимальную сумму для операции", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "1.1")
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)

class TestConfirmOrderStep(TestOrderCreationDialogs):
    def test_simple(self):
        self._create_order(stop_on_confirm=True)
        self.assertIn("Подтвердите параметры заказа", self.tg.outgoing[-1].text)

    def test_confirm(self):
        self._create_order(stop_on_confirm=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="place_order")
        self.assertIn("Поздравляем! Ваш заказ размещен", self.tg.outgoing[-2].text)

    def test_cancel(self):
        self._create_order(stop_on_confirm=True)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="cancel")
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)

    # Addtionally we test SetMinOpThresholdStep and SetLifetimeStep
        
