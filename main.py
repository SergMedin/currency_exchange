from lib.tg_app import TgApp
from lib.tg import TelegramMock
from lib.db_sqla import SqlDb

tg = TelegramMock()  # TODO: real Telegram
db = SqlDb()  # TODO: real file
app = TgApp(db, tg)
