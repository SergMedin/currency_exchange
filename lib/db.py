from typing import Callable
from .data import Order


class Db:
    def get_order(self, id: int) -> Order:
        raise NotImplementedError()

    def store_order(self, o: Order) -> Order:
        raise NotImplementedError()

    def update_order(self, o: Order):
        raise NotImplementedError()

    def remove_order(self, id: int):
        raise NotImplementedError()

    def iterate_orders(self, callback: Callable[[Order], None]):
        raise NotImplementedError()
