from .db import Db
from .tg import Tg, TgMsg
from .exchange import Exchange
from .data import Match, Order, User, OrderType
from decimal import Decimal, InvalidOperation


class TgApp:
    def __init__(self, db: Db, tg: Tg):
        self._db = db
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message  # FIXME: questionable design. Fix it later
        self._ex = Exchange(self._db, self._on_match)

    def _on_incoming_tg_message(self, m: TgMsg):
        def _check_currencies(c1: str, c2: str) -> None:
            if c1 not in ['rub'] or c2 not in ['amd']:
                raise ValueError("Invalid currency")

        def _check_price(price: str) -> None:
            try:
                price = Decimal(price)
                if price != price.quantize(Decimal('0.00')):
                    raise ValueError("Price has more than two digits after the decimal point")
            except InvalidOperation:
                raise ValueError("Invalid value for Decimal")
        
        def _check_amount(amount: Decimal) -> None:
            if amount <= 0:
                raise ValueError("Amount cannot be negative or zero")

        def _check_min_op_threshold(amount: Decimal, min_op_threshold: Decimal) -> None:
            if min_op_threshold < 0:
                raise ValueError("Minimum operational threshold cannot be negative")
            if min_op_threshold > amount:
                raise ValueError("Minimum operational threshold cannot be greater than the amount")

        # ['buy', '1500', 'usd', '*', '98.1', 'rub', 'min_amt', '100']
        #  0      1       2      3    4       5      6          7
        pp = m.text.lower().strip().split(" ")
        # print("INC TG MSG:", m, pp)
        _check_amount(Decimal(pp[1]))
        _check_min_op_threshold(Decimal(pp[1]), Decimal(pp[7]))
        _check_price(pp[4])
        _check_currencies(pp[2], pp[5])

        if pp[0] == "buy":
            ot = OrderType.BUY
        elif pp[0] == "sell":
            ot = OrderType.SELL
        else:
            raise ValueError("Invalid order type")

        amount = Decimal(pp[1])
        price = Decimal(pp[4])
        o = Order(User(m.user_id), ot, price, amount)
        self._ex.on_new_order(o)

    def _on_match(self, m: Match):
        buyer_id = m.buy_order.user.id
        seller_id = m.sell_order.user.id
        message_buyer = f"Go and buy {m.amount} from {seller_id} for {m.price} per unit"
        message_seller = f"You should sell {m.amount} to {buyer_id} for {m.price} per unit"
        self._tg.send_message(TgMsg(buyer_id, message_buyer))
        self._tg.send_message(TgMsg(seller_id, message_seller))
