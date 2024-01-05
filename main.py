from lib.tg import TelegramReal
from lib.tg_app import TgApp
from lib.db_sqla import SqlDb


if __name__ == "__main__":
    telegram = TelegramReal()
    app = TgApp(db=SqlDb("sqlite:///exchange_database.sqlite"), tg=telegram)
    telegram.run_forever()
