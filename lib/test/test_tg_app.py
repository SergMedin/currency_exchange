import unittest
import os

from ..application import Application
from ..botlib.tg import TelegramMock
from ..currency_rates import CurrencyMockClient
from ..db_sqla import SqlDb


class TestTgApp(unittest.TestCase):

    def setUp(self):
        self.admin_contacts = [3, 4, 5]
        self.tg = TelegramMock()
        self.db = SqlDb()
        self.app = Application(
            self.db,
            self.tg,
            currency_client=CurrencyMockClient(),
            admin_contacts=self.admin_contacts,
        )

    # def test_start_command(self):
    #     self.tg.emulate_incoming_message(1, "Joe", "/start")
    #     self.assertEqual(3, len(self.tg.outgoing))
    #     m = self.tg.outgoing[-1]
    #     self.assertEqual("Joe", m.user_name)
    #     self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)
    #     self.assertEqual("Markdown", m.parse_mode)

    # def test_help_command(self):
    #     self.tg.emulate_incoming_message(1, "Joe", "/help")
    #     self.assertEqual(1, len(self.tg.outgoing))
    #     m = self.tg.outgoing[0]
    #     self.assertIn("Operating Currency Pair", m.text)
    #     self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
    #     m = self.tg.outgoing[-1]
    #     self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)

    # def test_help_text(self):
    #     self.tg.emulate_incoming_message(1, "Joe", "Help")
    #     self.assertEqual(1, len(self.tg.outgoing))
    #     m = self.tg.outgoing[0]
    #     self.assertIn("Operating Currency Pair", m.text)
    #     self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
    #     m = self.tg.outgoing[-1]
    #     self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)

    # def test_statistic_button(self):
    #     self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="statistics")
    #     self.assertEqual(2, len(self.tg.outgoing))
    #     m = self.tg.outgoing[-1]
    #     self.assertIn("Current exchange rate:", m.text)
    #     self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
    #     m = self.tg.outgoing[-1]
    #     self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)

    # def test_my_orders_button(self):
    #     self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="my_orders")
    #     self.assertEqual(3, len(self.tg.outgoing))
    #     self.assertEqual(1, self.tg.outgoing[0].edit_message_with_id)
    #     self.assertIn("У вас нет активных заявок", self.tg.outgoing[1].text)
    #     self.tg.emulate_incoming_message(1, "Joe", "", keyboard_callback="back")
    #     m = self.tg.outgoing[-1]
    #     self.assertEqual("create_order", m.inline_keyboard[0][0].callback_data)

    def test_simple_match(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            2, "Dow", "/add BUY 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        # four messages: two about the added orders, two about the match
        self.assertEqual(4 + len(self.admin_contacts), len(self.tg.outgoing))
        self.assertTrue(
            "match!\n\nsell_order:\n\tuser: @Joe (1)\n\tprice: 98.1000 AMD/RUB\n\tamount_initial: 1500.00 RUB\n"
            "\tamount_left: 0.00 RUB\n\tmin_op_threshold: 100.00 RUB\n\tlifetime_sec: 1 hours"
            in self.tg.outgoing[-1].text,
        )

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
        self.assertEqual(6 + len(self.admin_contacts), len(self.tg.outgoing))
        self.assertIn(
            "по цене 98.1000 за единицу",
            self.tg.outgoing[-1 - len(self.admin_contacts)].text,
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
