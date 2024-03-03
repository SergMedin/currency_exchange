#!/usr/bin/env python
import logging
import os

from dotenv import load_dotenv

from lib.botlib.tg import TelegramReal
from lib.currency_rates import CurrencyFreaksClient
from lib.application import Application
from lib.comms.mailer import Mailer, MailerReal, MailerMock
from lib.db_sqla import SqlDb
from lib.logger import setup_logging
from lib.rep_sys.rep_sys import ReputationSystem
from lib.rep_sys import rep_id


if __name__ == "__main__":
    load_dotenv()
    setup_logging()
    conn_str = os.getenv("EXCH_DB_CONN_STRING", "sqlite:///exchange_database.sqlite")
    tg_token = os.environ["EXCH_TG_TOKEN"]
    print(f"tg_token: ...{tg_token[-5:]}" if tg_token else "tg_token: None")
    telegram = TelegramReal(token=tg_token)
    currency_client = CurrencyFreaksClient(os.environ["EXCH_CURRENCYFREAKS_TOKEN"])
    try:
        email_user = os.environ["EMAIL_USER"]
        email_app_password = os.environ["EMAIL_APP_PASSWORD"]
        email_server = os.environ["EMAIL_SERVER"]
        email_port = os.environ["EMAIL_PORT"]
        email_allowed_mails_domain = os.environ.get("PERMITTED_MAIL_DOMAINS")

        mailer: Mailer = MailerReal(
            server=email_server,
            port=int(email_port),
            user=email_user,
            app_password=email_app_password,
            allowed_mail_destinations=email_allowed_mails_domain,
        )
    except:
        mailer = MailerMock()
        logging.exception("Failed to create MailerReal, using MailerMock")

    try:
        rep_id.EMAIL_SALT = os.environ["EMAIL_SALT"]
    except KeyError:
        logging.warning("Using default EMAIL_SALT")

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
        mailer=mailer,
    )

    print("Wating for TG messages")
    telegram.run_forever()
