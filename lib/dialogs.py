import os
from bootshop.stories import (
    Controller,
    Event,
    OutMessage,
    Button,
    Message,
    Command,
    ButtonAction,
)
from .lazy_load import LazyMessageLoader


_help_message_loader = LazyMessageLoader(
    os.path.join(os.path.dirname(__file__), "tg_messages", "help_message.md")
)


class Main(Controller):
    def __init__(self):
        with open("./lib/tg_messages/start_message.md", "r") as f:
            tg_start_message = f.read().strip()
        super().__init__(
            text=tg_start_message,
            parse_mode="Markdown",
            buttons=[
                [Button("Create order"), Button("My orders")],
                [Button("Statistics"), Button("Help")],
            ],
        )
        self._a2c = {
            "create order": CreateOrder,
            "my orders": MyOrders,
            "statistics": Statistics,
            "help": Help,
        }

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, Command):
            if e.name == "start":
                return self.render()
            elif e.name == "help":
                return self.show_child(Help(self))
            else:
                raise ValueError(f"Unknown command: {e.name}")
        elif isinstance(e, Message):
            if e.text.lower() == "help":
                return self.show_child(Help(self))
            raise ValueError(f"Unknown message: {e.text}")
        elif isinstance(e, ButtonAction):
            return self.show_child(self._a2c[e.name](self))
        raise NotImplementedError()


class CreateOrder(Controller):
    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Choose a product:",
            buttons=[
                [Button("Shoes"), Button("Socks")],
                [Button("Back")],
            ],
        )
        self._a2c = {
            "shoes": CreateOrder,
            "socks": CreateOrder,
            "back": Main,
        }

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            return self.show_child(self._a2c[e.name](self))
        raise NotImplementedError()


class MyOrders(Controller):
    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="My orders",
            buttons=[[Button("Order 1"), Button("Order 2")], [Button("Back")]],
        )
        self._a2c = {
            "order 1": MyOrders,
            "order 2": MyOrders,
            "back": Main,
        }

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            return self.show_child(self._a2c[e.name](self))
        raise NotImplementedError()


class Statistics(Controller):
    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Statistics",
            buttons=[[Button("Back")]],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            return self.close()
        raise NotImplementedError()


class Help(Controller):
    def __init__(self, parent: Controller):
        text = _help_message_loader.message
        super().__init__(
            parent=parent,
            text=text,
            parse_mode="Markdown",
            buttons=[[Button("Back")]],
        )

    def process_event(self, e: Event) -> OutMessage:
        return self.close()
