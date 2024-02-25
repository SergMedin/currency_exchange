#!/usr/bin/env python

from dotenv import load_dotenv
import os
from lib.botlib.tg import TelegramReal
from lib.currency_rates import CurrencyFreaksClient
from lib.application import Application
from lib.db_sqla import SqlDb
from lib.logger import setup_logging
from lib.rep_sys.rep_sys import ReputationSystem


if __name__ == "__main__":
    load_dotenv()
    setup_logging()
    conn_str = os.getenv("EXCH_DB_CONN_STRING", "sqlite:///exchange_database.sqlite")
    tg_token = os.environ["EXCH_TG_TOKEN"]
    print(f"tg_token: ...{tg_token[-5:]}" if tg_token else "tg_token: None")
    telegram = TelegramReal(token=tg_token)
    currency_client = CurrencyFreaksClient(os.environ["EXCH_CURRENCYFREAKS_TOKEN"])

    try:
        admin_contacts_raw = os.environ["ADMINS_TG"]
    except KeyError:
        admin_contacts = None
    else:
        admin_contacts = list(map(int, admin_contacts_raw.strip().split(",")))

    db = SqlDb(conn_str)
    app = Application(
        db=db,
        tg=telegram,
        currency_client=currency_client,
        admin_contacts=admin_contacts,
        rep_sys=ReputationSystem(db.engine),
    )

    print("Wating for TG messages")
    telegram.run_forever()
