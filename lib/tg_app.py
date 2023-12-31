from .db import Db
from .tg import Tg, TgMsg
from .exchange import Exchange
from .data import Match, Order, User, OrderType
from decimal import Decimal


class TgApp:
    def __init__(self, db: Db, tg: Tg):
        self._db = db
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message  # FIXME: questionable design. Fix it later
        self._ex = Exchange(self._db, self._on_match)

    def _on_incoming_tg_message(self, m: TgMsg):
        # ['buy', '1500', 'usd', '*', '98.1', 'rub']
        #  0      1       2      3    4       5
        pp = m.text.lower().split(" ")
        # print("INC TG MSG:", m, pp)
        ot = OrderType.BUY if pp[0] == "buy" else OrderType.SELL
        amt = Decimal(pp[1])
        price = Decimal(pp[4])
        o = Order(User(m.user_id), ot, price, amt)
        self._ex.on_new_order(o)

    def _on_match(self, m: Match):
        buyer_id = m.buy_order.user.id
        seller_id = m.sell_order.user.id
        self._tg.send_message(TgMsg(buyer_id, f"Go and by {m.amount} from {seller_id} for {m.price} per unit"))
        self._tg.send_message(TgMsg(seller_id, f"You should sell {m.amount} to {buyer_id} for {m.price} per unit"))
