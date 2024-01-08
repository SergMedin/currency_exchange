from dotenv import load_dotenv
import os
import threading
import dataclasses
import time
import logging
from typing import Dict
from lib.tg import TelegramReal, Tg, TgMsg
from lib.gspreads import GSpreadsTable, GSpreadsTableMock

# Привет! Какой нужен каблук?
# (Варианты 7 8 8,5 9 9,5 10 10,5 хочу попробовать разные)
# Размер (линейка размеров, хочу попробовать разные)


@dataclasses.dataclass
class GoogleSheetsConfig:
    mock: GSpreadsTableMock = None
    credential_filepath: str = None
    spreadsheet_key: str = None
    worksheet_title: str = None


@dataclasses.dataclass
class Stock:
    size: str
    amount: int


@dataclasses.dataclass
class Stocks:
    mtime: float = dataclasses.field(default_factory=lambda: time.time())
    sizes: Dict[str, Stock] = dataclasses.field(default_factory=dict)


MAGIC_SPEC_SIZE = "спец"
BOOT_SIZE_MIN = 25
BOOT_SIZE_MAX = 52


class ShoesShopApp:

    def __init__(self, tg: Tg, gsheets_config: GoogleSheetsConfig = None):
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message
        c = gsheets_config
        if c and c.credential_filepath and not c.mock:
            self.gs = GSpreadsTable(c.credential_filepath, c.spreadsheet_key, c.worksheet_title)
        else:
            self.gs = GSpreadsTableMock() if not c or c.mock is None else c.mock
        self._stocks = Stocks()
        self._load_data()

    def _on_incoming_tg_message(self, m: TgMsg):
        print("BOOTSGHOP: new tg msg:", m)
        self._tg.send_message(TgMsg(m.user_id, m.user_name, "I am a bit stupid yet"))

    def _load_data(self):
        logging.info("Updating stocks from Google Spreads: start")
        cmp_to = ["Total", "Size"]
        hdr1, hdr2 = self.gs.cell(1, 1), self.gs.cell(1, 2)
        if [hdr1, hdr2] != cmp_to:
            logging.error(f"Wrong heading of Google Sheets table: {[hdr1, hdr2]} while {cmp_to} expected")
            return

        def is_int(s):
            try:
                int(s)
                return True
            except ValueError:
                return False
        row = 2
        s = Stocks()
        while True:
            amt, size = self.gs.cell(row, 1), self.gs.cell(row, 2)
            if not amt and not size:
                break
            if not is_int(amt) or (not is_int(size) and size != MAGIC_SPEC_SIZE):
                logging.error(f"Looks like row #{row} in Google Spreadas has wrong format: {[amt, size]}")
            else:
                amt = int(amt)
                if amt < 0 or amt > 100:
                    logging.error(f"Amount in row #{row} looks suspicious")
                s.sizes[size] = Stock(size, amt)
            row += 1
        s.mtime = time.time()
        self._stocks = s  # hope GIL helps
        logging.info("Updating stocks from Google Spreads: end")


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
