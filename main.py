from dotenv import load_dotenv
import os
from lib.tg import TelegramReal
from lib.tg_app import TgApp
from lib.db_sqla import SqlDb


if __name__ == "__main__":
    load_dotenv()
    conn_str = os.getenv("EXCH_DB_CONN_STRING", "sqlite:///exchange_database.sqlite")
    telegram = TelegramReal()
    app = TgApp(db=SqlDb(conn_str), tg=telegram)
    telegram.run_forever()
