import unittest
import os

from ..application import Application
from ..tg import TelegramMock
from ..currency_rates import CurrencyMockClient
from ..db_sqla import SqlDb


class TestTgApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if os.path.exists("./tg_data/app_db.json"):
            os.remove("./tg_data/app_db.json")

    def setUp(self):
        self.tg = TelegramMock()
        self.tg.admin_contacts = [3, 4, 5]
        self.db = SqlDb()
        self.app = Application(self.db, self.tg, currency_client=CurrencyMockClient())

    def test_start_command(self):
        self.tg.emulate_incoming_message(1, "Joe", "/start")
        self.assertEqual(3, len(self.tg.outgoing))
        m = self.tg.outgoing[-1]
        self.assertEqual("Joe", m.user_name)
        self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)
        self.assertEqual("Markdown", m.parse_mode)

    def test_help_command(self):
        self.tg.emulate_incoming_message(1, "Joe", "/help")
        self.assertEqual(1, len(self.tg.outgoing))
        m = self.tg.outgoing[0]
        self.assertIn("Operating Currency Pair", m.text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
        m = self.tg.outgoing[-1]
        self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)

    def test_help_text(self):
        self.tg.emulate_incoming_message(1, "Joe", "Help")
        self.assertEqual(1, len(self.tg.outgoing))
        m = self.tg.outgoing[0]
        self.assertIn("Operating Currency Pair", m.text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
        m = self.tg.outgoing[-1]
        self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)

    def test_statistic_button(self):
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="statistics")
        self.assertEqual(2, len(self.tg.outgoing))
        m = self.tg.outgoing[-1]
        self.assertIn("Current exchange rate:", m.text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
        m = self.tg.outgoing[-1]
        self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)

    def test_my_orders_button(self):
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="my_orders")
        self.assertEqual(3, len(self.tg.outgoing))
        self.assertEqual(1, self.tg.outgoing[0].edit_message_with_id)
        self.assertIn("У вас нет активных заявок", self.tg.outgoing[1].text)
        self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
        m = self.tg.outgoing[-1]
        self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)

    def test_simple_match(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            2, "Dow", "/add BUY 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        # four messages: two about the added orders, two about the match
        self.assertEqual(4 + len(self.tg.admin_contacts), len(self.tg.outgoing))

    def test_simple_no_match(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            2, "Dow", "/add BUY 1500 RUB * 98.01 AMD min_amt 100 lifetime_h 1"
        )
        self.assertEqual(2, len(self.tg.outgoing))

    def test_simple_best_price(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            2, "Dow", "/add SELL 1500 RUB * 100 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            3, "KarlMax", "/add SELL 1500 RUB * 110 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            100, "Kate", "/add BUY 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        # six messages: four about the added orders, two about the match, two messages for admins
        self.assertEqual(6 + len(self.tg.admin_contacts), len(self.tg.outgoing))
        self.assertIn(
            "по цене 98.1000 за единицу",
            self.tg.outgoing[-1 - len(self.tg.admin_contacts)].text,
        )

    def test_check_price_valid(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * 4.54 AMD min_amt 100 lifetime_h 1"
        )

    def test_check_price_invalid_decimal(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * 4.54111 AMD min_amt 100 lifetime_h 1"
        )
        self.assertIn(
            "Price has more than four digits after the decimal point",
            self.tg.outgoing[0].text,
        )

    def test_check_price_invalid_value(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * INVALID AMD min_amt 100 lifetime_h 1"
        )
        self.assertIn("Invalid value for Decimal", self.tg.outgoing[0].text)

    def test_check_min_op_threshold_negative_value(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * 4.54 AMD min_amt -100 lifetime_h 1"
        )
        self.assertEqual(
            "Error: Minimum operational threshold cannot be negative",
            self.tg.outgoing[0].text,
        )

    def test_on_incoming_tg_message_start_command(self):
        self.tg.emulate_incoming_message(1, "Joe", "/start")
        self.assertEqual(3, len(self.tg.outgoing))
        self.assertEqual("Joe", self.tg.outgoing[0].user_name)
        with open(
            "./lib/dialogs/tg_messages/start_message.md",
            "r",
            encoding="UTF-8",
            errors="ignore",
        ) as f:
            tg_start_message = f.read().strip()
        self.assertEqual(tg_start_message, self.tg.outgoing[1].text)

    def test_on_incoming_tg_message_remove_command(self):
        self.tg.emulate_incoming_message(1, "Joe", "/remove 12345")
        self.assertEqual(1, len(self.tg.outgoing))
        self.assertIn("Error: Invalid order id: 12345", self.tg.outgoing[0].text)
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * 4.54 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(1, "Joe", "/remove 1")
        self.assertEqual(3, len(self.tg.outgoing))
        self.assertEqual("Order with id 1 was removed", self.tg.outgoing[-1].text)

    def test_on_incoming_tg_message_invalid_command(self):
        self.tg.emulate_incoming_message(1, "Joe", "/invalid")
        self.assertEqual(1, len(self.tg.outgoing))
        self.assertEqual("Error: Invalid command: /invalid", self.tg.outgoing[0].text)

    def test_on_incoming_tg_message_group_message(self):
        self.tg.emulate_incoming_message(
            -1, "Group", "/add SELL 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        self.assertEqual(1, len(self.tg.outgoing))
        self.assertIn("Error: We don't work with groups yet", self.tg.outgoing[0].text)


class TestTGAppSM(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if os.path.exists("./tg_data/app_db.json"):
            os.remove("./tg_data/app_db.json")

    def setUp(self):
        self.tg = TelegramMock()
        self.db = SqlDb()
        self.app = Application(self.db, self.tg, currency_client=CurrencyMockClient())

    def _bot_start(self):
        self.tg.emulate_incoming_message(1, "Joe", "/start")
        self.assertEqual("Joe", self.tg.outgoing[-1].user_name)
        with open("./lib/dialogs/tg_messages/start_message.md", "r") as f:
            tg_start_message = f.read().strip()
        self.assertEqual(tg_start_message, self.tg.outgoing[-1].text)

    def _sm_entrance(self):
        self.tg.emulate_incoming_message(1, "Joe", "Create order")
        text = (
            "Current statistics (to get the full statistics, while being in main menu send '/stat' command"
            " or press Statistics button):"
            "\n  * last match price: None"
            "\n  * best buyer price: No buyers yet"
            "\n  * best seller price: No sellers yet"
            "\n\nChoose the type of order"
        )
        self.assertEqual(text, self.tg.outgoing[-1].text)

    def _sm_type_invalid(self):
        self.tg.emulate_incoming_message(1, "Joe", "Обменяться телами")
        self.assertEqual(
            "Error: Invalid order type: Обменяться телами", self.tg.outgoing[-1].text
        )

    def _sm_type_valid(self):
        self.tg.emulate_incoming_message(1, "Joe", "Buy rubles")
        self.assertEqual(
            "Enter the amount to exchange (RUB)", self.tg.outgoing[-1].text
        )

    def _sm_currency_from_invalid(self):
        self.tg.emulate_incoming_message(1, "Joe", "Йены")
        self.assertEqual("Error: Invalid currency: Йены", self.tg.outgoing[-1].text)

    def _sm_currency_from_valid(self):
        self.tg.emulate_incoming_message(1, "Joe", "RUB")
        self.assertEqual("Выберите целевую валюту", self.tg.outgoing[-1].text)

    def _sm_currency_to_invalid(self):
        self.tg.emulate_incoming_message(1, "Joe", "Тугрики")
        self.assertEqual("Error: Invalid currency: Тугрики", self.tg.outgoing[-1].text)

    def _sm_currency_to_valid(self):
        self.tg.emulate_incoming_message(1, "Joe", "AMD")
        self.assertEqual("Введите сумму для обмена", self.tg.outgoing[-1].text)

    def _sm_amount_invalid(self):
        self.tg.emulate_incoming_message(1, "Joe", "1000.0")
        self.assertEqual("Error: Invalid amount: 1000.0", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "0")
        self.assertEqual(
            "Error: Amount cannot be negative or zero", self.tg.outgoing[-1].text
        )
        self.tg.emulate_incoming_message(1, "Joe", "-1000")
        self.assertEqual(
            "Error: Invalid amount: -1000", self.tg.outgoing[-1].text
        )  # FIXME: Should be "Amount cannot be negative or zero"

    def _sm_amount_valid(self):
        self.tg.emulate_incoming_message(1, "Joe", "1000")
        self.assertEqual(
            "Choose the type of rate",
            self.tg.outgoing[-1].text,
        )

    def _sm_type_price_valid(self):
        self.tg.emulate_incoming_message(1, "Joe", "Absolute")
        self.assertEqual(
            "Enter the desired exchange rate in AMD/RUB. For example: 4.54",
            self.tg.outgoing[-1].text,
        )

    def _sm_price_invalid(self):
        self.tg.emulate_incoming_message(1, "Joe", "INVALID")
        self.assertEqual(
            "Error: Invalid value for Decimal: INVALID", self.tg.outgoing[-1].text
        )
        self.tg.emulate_incoming_message(1, "Joe", "0")
        self.assertEqual(
            "Error: Price cannot be negative or zero", self.tg.outgoing[-1].text
        )
        self.tg.emulate_incoming_message(1, "Joe", "-1000")
        self.assertEqual(
            "Error: Price cannot be negative or zero", self.tg.outgoing[-1].text
        )

    def _sm_price_valid(self):
        self.tg.emulate_incoming_message(1, "Joe", "98.1")
        self.assertEqual(
            "Enter the minimum operational threshold in RUB", self.tg.outgoing[-1].text
        )

    def _sm_min_op_threshold_invalid(self):
        self.tg.emulate_incoming_message(1, "Joe", "INVALID")
        self.assertEqual(
            "Error: Invalid value for Decimal: INVALID", self.tg.outgoing[-1].text
        )
        self.tg.emulate_incoming_message(1, "Joe", "1001")
        self.assertEqual(
            "Error: Minimum operational threshold cannot be greater than the amount",
            self.tg.outgoing[-1].text,
        )
        self.tg.emulate_incoming_message(1, "Joe", "-1000")
        self.assertEqual(
            "Error: Minimum operational threshold cannot be negative",
            self.tg.outgoing[-1].text,
        )

    def _sm_min_op_treshhold_valid(self):
        self.tg.emulate_incoming_message(1, "Joe", "100")
        self.assertEqual(
            "Enter the lifetime of the order in hours",
            self.tg.outgoing[-1].text,
        )

    def _sm_lifetime_invalid(self):
        self.tg.emulate_incoming_message(1, "Joe", "INVALID")
        self.assertEqual("Error: Invalid lifetime: INVALID", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(1, "Joe", "49")
        self.assertEqual(
            "Error: Lifetime cannot be greater than 48 hours", self.tg.outgoing[-1].text
        )
        self.tg.emulate_incoming_message(1, "Joe", "-1")
        self.assertEqual(
            "Error: Invalid lifetime: -1", self.tg.outgoing[-1].text
        )  # FIXME: Should be "Lifetime cannot be negative"

    def _sm_lifetime_valid(self):
        self.tg.emulate_incoming_message(1, "Joe", "1")
        self.assertIn(
            "Confirm the order:",
            self.tg.outgoing[-1].text,
        )

    def _sm_confirm_invalid(self):
        self.tg.emulate_incoming_message(1, "Joe", "INVALID")
        self.assertEqual("Error: Invalid command: INVALID", self.tg.outgoing[-1].text)

    def _sm_confirm_accept(self):
        self.tg.emulate_incoming_message(1, "Joe", "Confirm")
        self.assertEqual("Заявка создана", self.tg.outgoing[-1].text)

    def _sm_confirm_reject(self):
        self.tg.emulate_incoming_message(1, "Joe", "Cancel")
        self.assertEqual("The order was canceled", self.tg.outgoing[-1].text)

    # def test_order_creation_sm(self):
    #     with self.subTest("Bot start"):
    #         self._bot_start()
    #     with self.subTest("Entrance"):
    #         self._sm_entrance()
    #     with self.subTest("Invalid Order type"):
    #         self._sm_type_invalid()
    #     with self.subTest("Valid Order type"):
    #         self._sm_type_valid()
    #     # with self.subTest("Invalid Currency"):
    #     #     self._sm_currency_from_invalid()
    #     # with self.subTest("Valid Currency"):
    #     #     self._sm_currency_from_valid()
    #     # with self.subTest("Invalid Currency"):
    #     #     self._sm_currency_to_invalid()
    #     # with self.subTest("Valid Currency"):
    #     #     self._sm_currency_to_valid()
    #     with self.subTest("Invalid Amount"):
    #         self._sm_amount_invalid()
    #     with self.subTest("Valid Amount"):
    #         self._sm_amount_valid()
    #     with self.subTest("Invalid Price"):
    #         self._sm_price_invalid()
    #     with self.subTest("Valid Price"):
    #         self._sm_price_valid()
    #     with self.subTest("Invalid Min Op Threshold"):
    #         self._sm_min_op_threshold_invalid()
    #     with self.subTest("Valid Min Op Threshold"):
    #         self._sm_min_op_treshhold_valid()
    #     with self.subTest("Invalid Lifetime"):
    #         self._sm_lifetime_invalid()
    #     with self.subTest("Valid Lifetime"):
    #         self._sm_lifetime_valid()
    #     with self.subTest("Invalid Confirm"):
    #         self._sm_confirm_invalid()
    #     with self.subTest("Confirm Accept"):
    #         self._sm_confirm_accept()

    # def test_order_cancel_sm(self):
    #     self._bot_start()
    #     self._sm_entrance()
    #     self._sm_type_valid()
    #     # self._sm_currency_from_valid()
    #     # self._sm_currency_to_valid()
    #     self._sm_amount_valid()
    #     self._sm_type_price_valid()
    #     self._sm_price_valid()
    #     self._sm_min_op_treshhold_valid()
    #     self._sm_lifetime_valid()
    #     with self.subTest("Confirm Reject"):
    #         self._sm_confirm_reject()
