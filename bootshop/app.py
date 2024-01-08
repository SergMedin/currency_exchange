from dotenv import load_dotenv
import os
import threading
from lib.tg import TelegramReal, Tg, TgMsg

# Привет! Какой нужен каблук?
# (Варианты 7 8 8,5 9 9,5 10 10,5 хочу попробовать разные)
# Размер (линейка размеров, хочу попробовать разные)


class ShoesShopApp:

    def __init__(self, tg: Tg):
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message

    def _on_incoming_tg_message(self, m: TgMsg):
        print("BOOTSGHOP: new tg msg:", m)


def init():
    load_dotenv()
    tg_token = os.getenv("BOOTSHOP_TG_TOKEN")
    telegram = TelegramReal(token=tg_token)
    ShoesShopApp(tg=telegram)
    return telegram


def start():
    telegram = init()
    threading.Thread(target=lambda: telegram.run_forever()).start()


if __name__ == "__main__":
    telegram = init()
    telegram.run_forever()
