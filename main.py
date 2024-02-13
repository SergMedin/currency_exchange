#!/usr/bin/env python

from dotenv import load_dotenv
import os
from lib.tg import TelegramReal
from lib.currency_rates import CurrencyFreaksClient
from lib.application import Application
from lib.db_sqla import SqlDb
from lib.logger import setup_logging


if __name__ == "__main__":
    load_dotenv()
    setup_logging()
    conn_str = os.getenv("EXCH_DB_CONN_STRING", "sqlite:///exchange_database.sqlite")
    tg_token = os.environ["EXCH_TG_TOKEN"]
    print(f"tg_token: ...{tg_token[-5:]}" if tg_token else "tg_token: None")
    zmq_orders_log_endpoint = os.getenv(
        "ZMQ_ORDERS_LOG_ENDPOINT", "inproc://orders.log"
    )
    spr_key = os.getenv(
        "GOOGLE_SPREADSHEET_KEY", "1k8yMmPNPwvyeknaGV0MGrVI2gfPFZ4hgH0yq-44xNJU"
    )
    telegram = TelegramReal(token=tg_token)
    currency_client = CurrencyFreaksClient(os.environ["EXCH_CURRENCYFREAKS_TOKEN"])

    admin_contacts_raw = os.getenv("ADMINS_TG", None)
    if admin_contacts_raw is not None:
        admin_contacts_raw = list(map(int, admin_contacts_raw.strip().split(",")))
    telegram.admin_contacts = admin_contacts_raw

    app = Application(
        db=SqlDb(conn_str),
        tg=telegram,
        currency_client=currency_client,
        zmq_orders_log_endpoint=zmq_orders_log_endpoint,
        log_spreadsheet_key=spr_key,
    )

    print("Wating for TG messages")
    telegram.run_forever()
    app.shutdown()
