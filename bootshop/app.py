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
    credential_filepath: str = None
    spreadsheet_key: str = None
    worksheet_title: str = None
    mock: GSpreadsTableMock = None


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
            logging.info("connecting Sheets API")
            self.gs = GSpreadsTable(c.credential_filepath, c.spreadsheet_key, c.worksheet_title)
        else:
            self.gs = GSpreadsTableMock() if not c or c.mock is None else c.mock
        self._stocks = Stocks()
        self._load_data()

    def _on_incoming_tg_message(self, m: TgMsg):
        logging.info(f"New tg msg: {m}")
        try:
            pp = m.text.split()
            first = pp[0].lower()
            if first.startswith("/"):
                cmds = {
                    "sizes": self._on_cmd_sizes,
                    "reload": self._on_cmd_reload_stocks,
                }
                cmd = first[1:]
                if cmd in cmds:
                    cmds[cmd](m, pp[1:])
                else:
                    self._tg.send_message(TgMsg(m.user_id, m.user_name, f"Unknown command: {cmd}"))
            else:
                self._tg.send_message(TgMsg(m.user_id, m.user_name, f"Dunno what to do with {m.text}"))
        except Exception as e:
            self._tg.send_message(TgMsg(m.user_id, None, str(e)))
            raise

    def _load_data(self):
        logging.info("Updating stocks from Google Spreads: start")
        cmp_to = ["Всего", "Размеры"]
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
        row = 3
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
        self._stocks = s
        count = len(s.sizes)
        logging.info(f"Updating stocks from Google Spreads: loaded {count} rows")

    def _on_cmd_sizes(self, m: TgMsg, args: list):
        m = ["В наличиии размеры:"]
        for s in sorted(s for s, st in self._stocks.sizes.items() if st.amount > 0):
            m.append(f"* {s}")
        txt = "\n".join(m)
        self._tg.send_message(TgMsg(m.user_id, None, txt))

    def _on_cmd_reload_stocks(self, m: TgMsg, args: list):
        self._load_data()


def init():
    load_dotenv()
    tg_token = os.getenv("BOOTSHOP_TG_TOKEN")
    gs_cred_filename = os.getenv("BOOTSHOP_GS_CRED_FILENAME")
    gs_key = os.getenv("BOOTSHOP_GS_KEY")
    gs_sheet = os.getenv("BOOTSHOP_GS_SHEET")
    gs_cfg = GoogleSheetsConfig(gs_cred_filename, gs_key, gs_sheet)
    telegram = TelegramReal(token=tg_token)
    ShoesShopApp(tg=telegram, gsheets_config=gs_cfg)
    return telegram


def start():
    telegram = init()
    threading.Thread(target=lambda: telegram.run_forever()).start()


if __name__ == "__main__":
    telegram = init()
    telegram.run_forever()
