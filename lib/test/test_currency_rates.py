import unittest
from unittest.mock import patch
import requests
from ..currency_rates import CurrencyFreaksClient
import sys
import os
import time

# строка ниже нужна для того, чтобы работали строки вроде @patch("currency_rates.requests.get")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestCurrencyFreaksClient(unittest.TestCase):
    @patch("currency_rates.requests.get")
    def test_update_rates_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"rates": {"RUB": 78.5, "AMD": 520.75}}
        client = CurrencyFreaksClient("API_KEY")
        client.update_rates()
        self.assertEqual(client.get_rate("RUB")["rate"], 78.5)
        self.assertEqual(client.get_rate("AMD")["rate"], 520.75)

    @patch("currency_rates.requests.get")
    def test_update_rates_failure(self, mock_get):
        mock_get.return_value.status_code = 500
        client = CurrencyFreaksClient("API_KEY")
        client.update_rates()
        self.assertEqual(client.get_rate("RUB")["rate"], None)
        self.assertEqual(client.get_rate("AMD")["rate"], None)

    @patch("currency_rates.requests.get")
    def test_update_rates_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        client = CurrencyFreaksClient("API_KEY")
        client.update_rates()
        self.assertEqual(client.get_rate("RUB")["rate"], None)
        self.assertEqual(client.get_rate("AMD")["rate"], None)

    # @patch("currency_rates.requests.get")
    # def test_update_rates_retry_on_error(self, mock_get):
    #     mock_get.side_effect = [
    #         requests.exceptions.RequestException("Connection error"),
    #         MagicMock(
    #             status_code=200,
    #             json=MagicMock(return_value={"rates": {"RUB": 78.5, "AMD": 520.75}}),
    #         ),
    #     ]
    #     client = CurrencyFreaksClient("API_KEY")
    #     client.update_rates()
    #     self.assertEqual(client.get_rate("RUB"), 78.5)
    #     self.assertEqual(client.get_rate("AMD"), 520.75)

    @patch("currency_rates.requests.get")
    def test_schedule_rate_update(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "rates": {"RUB": 78.5, "AMD": 520.75},
            "date": "2024-01-21 00:00:00+00",
        }
        client = CurrencyFreaksClient("API_KEY")
        client.schedule_rate_update()
        # Wait for the update to happen
        time.sleep(2)
        self.assertEqual(client.get_rate("RUB")["rate"], 78.5)
        self.assertEqual(client.get_rate("AMD")["rate"], 520.75)


if __name__ == "__main__":
    unittest.main()
