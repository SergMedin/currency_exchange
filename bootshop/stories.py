from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserSession:
    user_id: int
    root_controller: "Controller"


@dataclass
class Event:
    user_id: int


@dataclass
class ButtonAction(Event):
    name: str


@dataclass
class Message(Event):
    text: str


@dataclass
class Button:
    text: str
    action: str

    def __init__(self, text: str, action: Optional[str] = None):
        self.text = text
        self.action = action if action else text.lower()

    def __post_init__(self):
        if self.action is None:
            self.action = self.text.lower()


@dataclass
class OutMessage:
    text: str
    buttons: list[Button] = field(default_factory=list)
    next: Optional["OutMessage"] = None

    def __add__(self, other: "OutMessage") -> "OutMessage":
        return OutMessage(self.text, self.buttons, other)


@dataclass
class Controller:
    parent: Optional["Controller"] = None
    child: Optional["Controller"] = None
    text: Optional[str] = ""
    buttons: list[Button] = field(default_factory=list)

    def process_event(self, e: Event) -> OutMessage:
        raise NotImplementedError()

    def render(self) -> OutMessage:
        if self.child:
            return self.child.render()
        else:
            return OutMessage(self.text if self.text else "", self.buttons)

    def show_child(self, child: "Controller") -> OutMessage:
        child.parent = self
        self.child = child
        return child.render()

    def close(self) -> OutMessage:
        if self.parent is None:
            raise ValueError("Can't close root controller")
        self.parent.child = None
        return self.parent.on_child_closed(self)

    def on_child_closed(self, child: "Controller") -> OutMessage:
        return self.render()


@dataclass
class YesNoController(Controller):
    result: Optional[bool] = None

    def __init__(self, parent: Controller, question: str):
        Controller.__init__(
            self,
            parent=parent,
            text=question,
            buttons=[Button("Yes", "yes"), Button("No", "no")],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            if e.name in ("yes", "no"):
                self.result = e.name == "yes"
                return self.close()
        raise ValueError("Unexpected event")
