import requests
import threading
from dotenv import load_dotenv
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


# FIXME: replace prints to logging (all code below)
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
                # response.json() :
                # {'date': '2024-01-21 00:00:00+00', 'base': 'USD', 'rates': {'AMD': '404.741979', 'RUB': '88.386974'}}
                if response.status_code == 200:
                    self.rates = response.json().get("rates", {})
                    self.date = response.json().get("date", None)
                    return
                else:
                    print(f"Error: Response code {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Connection error: {e}")
        print("Error: currency rates update failed")

    def schedule_rate_update(self):
        timer = RepeatTimer(6 * 60 * 60, self.update_rates)
        timer.daemon = True
        timer.start()


class CurrencyConverter:
    def __init__(self, currency_client=None):
        self.currency_client = currency_client

    def get_rate(self, from_currency, to_currency):
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
            print("Ошибка: не удалось найти курс для одной из валют.")
            return None


if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("EXCH_CURRENCYFREAKS_TOKEN")
    currency_client = CurrencyFreaksClient(api_key)

    converter = CurrencyConverter(currency_client)
    rate = converter.get_rate("RUB", "AMD")
    if rate:
        print(f"1 RUB = {rate['rate']:.4f} AMD on {rate['date'] }")

    converter = CurrencyConverter(CurrencyMockClient())
    rate = converter.get_rate("RUB", "AMD")
    if rate:
        print(f"1 RUB = {rate['rate']:.4f} AMD on {rate['date'] }")
