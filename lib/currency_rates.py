import requests  # type: ignore
import threading
import logging
import os
from decimal import Decimal


class CurrencyMockClient:
    def __init__(self):
        self.rates = {
            "RUB": 0.1000,
            "AMD": 0.4540,
        }

    def get_rate(self, currency):
        return {
            "rate": self.rates.get(currency),
            "date": "2021-01-01",
        }


class RepeatTimer(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class CurrencyFreaksClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.rates = {}
        self.date = None
        self.update_rates()
        self.schedule_rate_update()

    def get_rate(self, currency):
        return {
            "rate": self.rates.get(currency),
            "date": self.date,
        }

    def update_rates(self):
        attempt = 0
        while attempt < 3:
            try:
                attempt += 1
                response = requests.get(
                    f"https://api.currencyfreaks.com/v2.0/rates/latest?apikey={self.api_key}&symbols=RUB,AMD"
                )
                if response.status_code == 200:
                    self.rates = response.json().get("rates", {})
                    self.date = response.json().get("date", None)
                    return
                else:
                    logging.error(f"Error: Response code {response.status_code}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Connection error: {e}")
        logging.error("Error: currency rates update failed")

    def schedule_rate_update(self):
        timer = RepeatTimer(6 * 60 * 60, self.update_rates)
        timer.daemon = True
        timer.start()


class CurrencyConverter:
    def __init__(self, currency_client=None):
        self.currency_client = currency_client

    def get_rate(self, from_currency: str, to_currency: str):
        from_rate = self.currency_client.get_rate(from_currency)
        to_rate = self.currency_client.get_rate(to_currency)
        if from_rate and to_rate:
            rate = Decimal(to_rate["rate"]) / Decimal(from_rate["rate"])
            rounded_rate = rate.quantize(Decimal("0.0001"))
            return {
                "rate": rounded_rate,
                "date": to_rate["date"],
            }
        else:
            logging.error("Ошибка: не удалось найти курс для одной из валют.")
            return None
