from lib.tg import Tg
from lib.tg_app import TgApp
from lib.db_sqla import SqlDb


if __name__ == "__main__":
    telegram = TgApp(db=SqlDb(), tg=Tg())
