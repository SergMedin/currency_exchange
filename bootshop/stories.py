from dataclasses import dataclass, field
from enum import Enum


@dataclass
class StoryState:
    state: Enum
    substate: "StoryState"
    # substates: dict[Enum, "StoryState"] = field(default_factory=dict)


@dataclass
class UserSession:
    user_id: int
    state: StoryState


@dataclass
class Controller:
    # for_state: Enum
    pass


@dataclass
class StoryController(Controller):
    subcontrollers: dict[Enum, Controller] = field(default_factory=dict)


@dataclass
class Button:
    text: str
    action: str


@dataclass
class ScreenController(Controller):
    text: str = ""
    buttons: list[Button] = field(default_factory=list)

    def render(self):
        self._render_text()
        print("")
        self._render_buttons()

    def _render_text(self):
        print(self.text)

    def _render_buttons(self):
        s = " ".join([f"[{b.text}]" for b in self.buttons])
        print(s)


@dataclass
class Event:
    user_id: int


@dataclass
class Action(Event):
    name: str


@dataclass
class Message(Event):
    text: str


@dataclass
class Dispatcher:
    root: StoryController

    def dispath(self, s: UserSession, e: Event):
        pass


if __name__ == "__main__":
    class MainState(Enum):
        IDLE = 1
        ORDERING = 2
        ABOUT = 3

    class OrderingState(Enum):
        SIZE = 1
        KABLUK = 2
        PYATKA = 3
        COLOR = 4
        CONFIRM = 5
        CONFIRM_CANCELING = 100
        ENTER_OTHER = 200

    root = StoryController()

    main = ScreenController(text="Привет! Это магазин обуви. Чего желаете?",
                            buttons=[Button("Заказать", "order"), Button("О магазине", "about")])
    root.subcontrollers[MainState.IDLE] = main

    ord = StoryController(MainState.ORDERING)
    ord.subcontrollers[OrderingState.SIZE] = ScreenController(
        text="Выберите размер:", buttons=[
            Button("34"), Button("35"), Button("36"), Button("37"), Button("38"), Button("39"), Button("40"),
            Button("Другой"), Button("Отмена")
        ]
    )
    ord.subcontrollers[OrderingState.KABLUK] = ScreenController(
        text="Выберите размер:", buttons=[
            Button("3"), Button("9"), Button("10"), Button("85"), Button("105"),
            Button("Другой"), Button("Назад"), Button("Отмена")
        ]
    )
    ord.subcontrollers[OrderingState.CONFIRM] = ScreenController(
        text=None, buttons=[
            Button("Да, разместить заказ"), Button("Назад"), Button("Отмена")
        ]
    )
    ord.subcontrollers[OrderingState.CONFIRM_CANCELING] = ScreenController(
        text="Хотите прервать заказ?", buttons=[
            Button("Да"), Button("Нет")
        ]
    )

    root.subcontrollers[MainState.ABOUT] = ScreenController(
        text=("В [Название магазина] мы объединяем нашу любовь к аргентинскому танго с эксклюзивной коллекцией "
              "одежды, созданной, чтобы вы чувствовали себя неотразимо на танцполе. Наша одежда - это не просто "
              "костюмы, это произведения искусства, которые позволяют танцорам выразить себя в каждом движении."),
        buttons=[Button("Понятно")]
    )
