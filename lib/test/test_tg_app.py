import unittest
from ..tg_app import TgApp
from ..tg import TelegramMock
from ..db_sqla import SqlDb


class TestTgApp(unittest.TestCase):
    def setUp(self):
        self.tg = TelegramMock()
        self.db = SqlDb()
        self.app = TgApp(self.db, self.tg)

    def test_simple_match(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            2, "Dow", "/add BUY 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        # three messages: two about the added orders, two about the match
        self.assertEqual(4, len(self.tg.outgoing))

    def test_simple_no_match(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            2, "Dow", "/add BUY 1500 RUB * 98.01 AMD min_amt 100 lifetime_h 1"
        )
        # print('-'*80)
        # print(self.tg.outgoing)
        # print('-'*80)
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
        # print('-'*80)
        # for e in self.tg.outgoing:
        #     print(e)
        # print('-'*80)
        # six messages: four about the added orders, two about the match
        self.assertEqual(6, len(self.tg.outgoing))
        self.assertIn("for 98.10 per unit", self.tg.outgoing[-1].text)

    def test_check_price_valid(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * 4.54 AMD min_amt 100 lifetime_h 1"
        )

    def test_check_price_invalid_decimal(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * 4.541 AMD min_amt 100 lifetime_h 1"
        )
        self.assertIn(
            "Price has more than two digits after the decimal point",
            self.tg.outgoing[0].text,
        )

    def test_check_price_invalid_value(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * INVALID AMD min_amt 100 lifetime_h 1"
        )
        self.assertIn("Invalid value for Decimal", self.tg.outgoing[0].text)

    def test_check_min_op_threshold_negative_value(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * INVALID AMD min_amt -100 lifetime_h 1"
        )
        self.assertIn(
            "Error: Minimum operational threshold cannot be negative", self.tg.outgoing[0].text
        )

    def test_on_incoming_tg_message_start_command(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/start"
        )
        self.assertEqual(1, len(self.tg.outgoing))
        self.assertEqual("Joe", self.tg.outgoing[0].user_name)
        with open("./lib/tg_messages/start_message.md", "r") as f:
            tg_start_message = f.read().strip()
        self.assertEqual(tg_start_message, self.tg.outgoing[0].text)

    def test_on_incoming_tg_message_list_command(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/list"
        )
        self.assertEqual(1, len(self.tg.outgoing))
        self.assertEqual("You don't have any active orders", self.tg.outgoing[-1].text)
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * 4.54 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            1, "Joe", "/list"
        )
        self.assertIn('Your orders', self.tg.outgoing[-1].text)

    def test_on_incoming_tg_message_remove_command(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/remove 12345"
        )
        self.assertEqual(1, len(self.tg.outgoing))
        self.assertIn(
            "Error: Invalid order id: 12345", self.tg.outgoing[0].text
        )
        self.tg.emulate_incoming_message(
            1, "Joe", "/add SELL 1000 RUB * 4.54 AMD min_amt 100 lifetime_h 1"
        )
        self.tg.emulate_incoming_message(
            1, "Joe", "/remove 1"
        )
        self.assertEqual(3, len(self.tg.outgoing))
        self.assertEqual(
            "Order with id 1 was removed", self.tg.outgoing[-1].text
        )

    def test_on_incoming_tg_message_invalid_command(self):
        self.tg.emulate_incoming_message(
            1, "Joe", "/invalid"
        )
        self.assertEqual(1, len(self.tg.outgoing))
        self.assertEqual("Error: Invalid command: /invalid", self.tg.outgoing[0].text)

    def test_on_incoming_tg_message_group_message(self):
        self.tg.emulate_incoming_message(
            -1, "Group", "/add SELL 1500 RUB * 98.1 AMD min_amt 100 lifetime_h 1"
        )
        self.assertEqual(1, len(self.tg.outgoing))
        self.assertIn("Error: We don't work with groups yet", self.tg.outgoing[0].text)
