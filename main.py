#!/usr/bin/env python

from dotenv import load_dotenv
import os
from lib.tg import TelegramReal
from lib.application import Application
from lib.db_sqla import SqlDb


if __name__ == "__main__":
    load_dotenv()
    conn_str = os.getenv("EXCH_DB_CONN_STRING", "sqlite:///exchange_database.sqlite")
    tg_token = os.environ["EXCH_TG_TOKEN"]
    print("tg_token: ..." + tg_token[-5:])
    zmq_orders_log_endpoint = os.getenv(
        "ZMQ_ORDERS_LOG_ENDPOINT", "inproc://orders.log"
    )
    spr_key = os.getenv(
        "GOOGLE_SPREADSHEET_KEY", "1k8yMmPNPwvyeknaGV0MGrVI2gfPFZ4hgH0yq-44xNJU"
    )
    telegram = TelegramReal(token=tg_token)

    app = Application(
        db=SqlDb(conn_str),
        tg=telegram,
        zmq_orders_log_endpoint=zmq_orders_log_endpoint,
        log_spreadsheet_key=spr_key,
    )

    print("Wating for TG messages")
    telegram.run_forever()
    app.shutdown()
