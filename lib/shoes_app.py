from .tg import TgMsg, Tg

# Привет! Какой нужен каблук?
# (Варианты 7 8 8,5 9 9,5 10 10,5 хочу попробовать разные)
# Размер (линейка размеров, хочу попробовать разные)


class ShoesShopApp:

    def __init__(self, tg: Tg):
        self._tg = tg
        self._tg.on_message = self._on_incoming_tg_message

    def _on_incoming_tg_message(self, m: TgMsg):
        pass
