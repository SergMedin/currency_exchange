from decimal import Decimal
import time
from typing import Optional
from unittest.mock import patch

from lib.rep_sys.rep_id import RepSysUserId

from ..rep_sys.rep_sys import AUTH_REC_VALIDITY_SEC
from .base import ExchgTestBase


class TestMain(ExchgTestBase):

    def test_explicit_auth(self):
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="auth")
        self.assertIn("Введите ваш email", self.tg.outgoing[-1].text)

    def test_create_order_unauth(self):
        self.tg.emulate_incoming_message(
            222, "Noob", "", keyboard_callback="create_order"
        )
        self.assertIn("Вы не авторизованы", self.tg.outgoing[-2].text)
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)

    def test_auth_when_authenticated(self):
        self.rep_sys.set_authenticity(RepSysUserId(222), True)
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="auth")
        self.assertIn("Вы успешно авторизованы", self.tg.outgoing[-1].text)

    def test_auth_expiration(self):
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="auth")
        with patch("random.randint", return_value=1234):
            self.tg.emulate_incoming_message(222, "Noob", "email@example.com")
        self.tg.emulate_incoming_message(222, "Noob", "1234")
        self.assertIn("Вы успешно авторизованы", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="ok")
        with patch("time.time", return_value=time.time() + AUTH_REC_VALIDITY_SEC + 1):
            self.tg.emulate_incoming_message(
                222, "Noob", "", keyboard_callback="create_order"
            )
            self.assertIn("Вы не авторизованы", self.tg.outgoing[-2].text)
            self.assertIn("Выберите действие", self.tg.outgoing[-1].text)

    def test_email_milti_use_protection(self):
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="auth")
        with patch("random.randint", return_value=1234):
            self.tg.emulate_incoming_message(222, "Noob", "ab@example.com")
        self.tg.emulate_incoming_message(222, "Noob", "1234")
        self.assertIn("Вы успешно авторизованы", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="ok")

        self.rep_sys.set_authenticity(RepSysUserId(222), False)
        self.tg.emulate_incoming_message(
            222, "Noob", "", keyboard_callback="create_order"
        )
        self.assertIn("Вы не авторизованы", self.tg.outgoing[-2].text)
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="auth")
        self.assertIn("Введите ваш email", self.tg.outgoing[-1].text)

        self.tg.emulate_incoming_message(222, "Noob", "anoter@example.com")
        self.assertIn("Неверный email", self.tg.outgoing[-2].text)

        self.tg.emulate_incoming_message(777, "Noob", "", keyboard_callback="auth")
        self.tg.emulate_incoming_message(777, "Noob", "ab@example.com")
        self.assertIn("Неверный email", self.tg.outgoing[-2].text)


class TestEnterEmailStep(ExchgTestBase):
    def setUp(self):
        super().setUp()
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="auth")

    def test_ask_email(self):
        self.assertIn("Введите ваш email", self.tg.outgoing[-1].text)

    def test_cancel(self):
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="cancel")
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)

    def test_alternative(self):
        self.tg.emulate_incoming_message(
            222, "Noob", "", keyboard_callback="alternative"
        )
        self.assertIn("Напишите Сереге в телеграмме", self.tg.outgoing[-1].text)

    def test_bad_email(self):
        self.tg.emulate_incoming_message(222, "Noob", "hru-hru")
        self.assertIn("Invalid email", self.tg.outgoing[-2].text)

    def test_ok_email(self):
        self.tg.emulate_incoming_message(222, "Noob", "email@example.com")
        self.assertIn("Введите код:", self.tg.outgoing[-1].text)


class TestEnterCodeStep(ExchgTestBase):
    def setUp(self):
        super().setUp()
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="auth")
        with patch("random.randint", return_value=1234):
            self.tg.emulate_incoming_message(222, "Noob", "email@example.com")

    def test_ask_code(self):
        self.assertIn("Введите код:", self.tg.outgoing[-1].text)

    def test_cancel(self):
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="cancel")
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)

    def test_resend(self):
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="resend")
        self.assertIn("Введите ваш email", self.tg.outgoing[-1].text)

    def test_bad_code(self):
        self.tg.emulate_incoming_message(222, "Noob", "3454")
        self.assertIn("Неверный код", self.tg.outgoing[-2].text)

    def test_limit(self):
        self.tg.emulate_incoming_message(222, "Noob", "3454")
        self.assertIn("Неверный код", self.tg.outgoing[-2].text)
        self.tg.emulate_incoming_message(222, "Noob", "3454")
        self.assertIn("Неверный код", self.tg.outgoing[-2].text)
        self.tg.emulate_incoming_message(222, "Noob", "3454")
        self.assertIn("Неверный код", self.tg.outgoing[-2].text)
        self.tg.emulate_incoming_message(222, "Noob", "3454")
        self.assertIn(
            "Исчерпан лимит количества попыток или времени", self.tg.outgoing[-2].text
        )
        self.assertIn("Введите ваш email", self.tg.outgoing[-1].text)

    def test_correct_code(self):
        self.tg.emulate_incoming_message(222, "Noob", "1234")
        self.assertIn("Вы успешно авторизованы", self.tg.outgoing[-1].text)


class TestAuthenticatedStep(ExchgTestBase):
    def setUp(self):
        super().setUp()
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="auth")
        with patch("random.randint", return_value=1234):
            self.tg.emulate_incoming_message(222, "Noob", "email@example.com")
        self.tg.emulate_incoming_message(222, "Noob", "1234")

    def test_authed(self):
        self.assertIn("Вы успешно авторизованы", self.tg.outgoing[-1].text)

    def test_ok(self):
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="ok")
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)

    def test_create_order(self):
        self.tg.emulate_incoming_message(
            222, "Noob", "", keyboard_callback="create_order"
        )
        self.assertIn("Выберите тип заказа", self.tg.outgoing[-1].text)


class TestAuthAlternativeStep(ExchgTestBase):
    def setUp(self):
        super().setUp()
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="auth")
        self.tg.emulate_incoming_message(
            222, "Noob", "", keyboard_callback="alternative"
        )

    def test_alternative(self):
        self.assertIn("Напишите Сереге в телеграмме", self.tg.outgoing[-1].text)

    def test_ok(self):
        self.tg.emulate_incoming_message(222, "Noob", "", keyboard_callback="ok")
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)

    def test_closes_anyway(self):
        self.tg.emulate_incoming_message(222, "Noob", "hru-hru")
        self.assertIn("Выберите действие", self.tg.outgoing[-1].text)
