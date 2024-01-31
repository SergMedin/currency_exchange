from dataclasses import dataclass, field
from collections import OrderedDict
from enum import Enum
from typing import Optional, Union


@dataclass
class StoryState:
    state: Enum
    parent: Optional["StoryState"] = None
    substate: Optional["StoryState"] = None
    data: dict = field(default_factory=dict)

    def __repr__(self):
        return f"{self.state}({self.substate})"


@dataclass
class UserSession:
    user_id: int
    state: StoryState


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
class Controller:
    subcontrollers: OrderedDict[Enum, "Controller"] = field(default_factory=OrderedDict)

    def __init__(self, initial_state: Enum):
        self.subcontrollers = OrderedDict()
        self.initial_state = initial_state

    def render(self, s: StoryState):
        ctl = self.subcontrollers[s.state]
        if s.substate is None:
            s.substate = StoryState(ctl.initial_state, s)
        ctl.render(s.substate)

    def process_event(self, s: StoryState, e: Event):
        print(f"{self.__class__.__name__}.process_event: {e} => {s.state}")
        ctl = self.subcontrollers[s.state]
        if s.substate is None:
            s.substate = StoryState(ctl.initial_state, s)
        ctl.process_event(s.substate, e)

    def __repr__(self):
        lines = []
        lines.append(f"{self.__class__}")
        for sub_id, ctl in self.subcontrollers:
            pass


@dataclass
class Button:
    text: str
    action: Optional[str] = None

    def __post_init__(self):
        if self.action is None:
            self.action = self.text.lower()


@dataclass
class ScreenController(Controller):
    class ScreenState(Enum):
        SCREEN = 1

    text: str = ""
    buttons: list[Button] = field(default_factory=list)

    def __init__(self, text: str, buttons: Optional[list[Button]] = None):
        Controller.__init__(self, initial_state=ScreenController.ScreenState.SCREEN)
        self.text = text
        if buttons is None:
            buttons = []
        self.buttons = buttons

    def process_event(self, s: StoryState, e: Event):
        pass

    def render(self, _: StoryState):
        self._render_text()
        print("")
        self._render_buttons()

    def _render_text(self):
        print(self.text)

    def _render_buttons(self):
        s = " ".join([f"[{b.text}/{b.action}]" for b in self.buttons])
        print(s)


@dataclass
class Dispatcher:
    root: Controller

    def dispath(self, s: StoryState, e: Event):
        print(f"Dispatching {e} to {id(root)}")
        self.root.process_event(s, e)


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

    class MainController(Controller):
        class AboutController(ScreenController):
            def __init__(self):
                ScreenController.__init__(
                    self,
                    text=(
                        "В [Название магазина] мы объединяем нашу любовь к аргентинскому "
                        "танго с эксклюзивной коллекцией одежды, созданной, чтобы вы "
                        "чувствовали себя неотразимо на танцполе. Наша одежда - это не "
                        "просто костюмы, это произведения искусства, которые позволяют "
                        "танцорам выразить себя в каждом движении."
                    ),
                    buttons=[Button("Понятно", "ok")],
                )

            def process_event(self, s: StoryState, e: Event):
                ScreenController.process_event(self, s, e)
                print("AboutController.process_event")
                if isinstance(e, Action):
                    if s.parent is not None:
                        s.parent.state = MainState.IDLE
                    else:
                        raise Exception("AboutController.process_event: parent is None")
                elif isinstance(e, Message):
                    raise NotImplementedError()

        def __init__(self):
            Controller.__init__(self, initial_state=MainState.IDLE)
            self.subcontrollers[MainState.IDLE] = ScreenController(
                text="Привет! Это магазин обуви. Чего желаете?",
                buttons=[Button("Заказать", "order"), Button("О магазине", "about")],
            )
            self.subcontrollers[MainState.ORDERING] = OrderingController()
            self.subcontrollers[MainState.ABOUT] = MainController.AboutController()

        def process_event(self, s: StoryState, e: Event):
            Controller.process_event(self, s, e)
            if isinstance(e, Action):
                if e.name == "order":
                    s.state = MainState.ORDERING
                elif e.name == "about":
                    s.state = MainState.ABOUT
            elif isinstance(e, Message):
                raise NotImplementedError()

    class OrderingController(Controller):
        class SizeController(ScreenController):
            def __init__(self):
                ScreenController.__init__(
                    self,
                    text="Выберите размер:",
                    buttons=[
                        Button("34"),
                        Button("35"),
                        Button("36"),
                        Button("37"),
                        Button("38"),
                        Button("39"),
                        Button("40"),
                        Button("Другой"),
                        Button("Отмена"),
                    ],
                )

            def process_event(self, s: StoryState, e: Event):
                if isinstance(e, Action):
                    if e.name == "other":
                        s.state = OrderingState.ENTER_OTHER
                    elif e.name == "cancel":
                        s.state = MainState.IDLE
                    else:
                        size = int(e.name)
                        s.data["size"] = size
                        s.state = OrderingState.KABLUK
                elif isinstance(e, Message):
                    raise NotImplementedError()

        class KablukController(ScreenController):
            def __init__(self):
                ScreenController.__init__(
                    self,
                    text="Выберите каблук:",
                    buttons=[
                        Button("3"),
                        Button("9"),
                        Button("10"),
                        Button("85"),
                        Button("105"),
                        Button("Другой"),
                        Button("Назад"),
                        Button("Отмена"),
                    ],
                )

            def process_event(self, s: StoryState, e: Event):
                if isinstance(e, Action):
                    if e.name == "other":
                        s.state = OrderingState.ENTER_OTHER
                    elif e.name == "cancel":
                        s.state = MainState.IDLE
                    elif e.name == "back":
                        s.state = OrderingState.SIZE
                    else:
                        kabluk = int(e.name)
                        s.data["kabluk"] = kabluk
                        s.state = OrderingState.PYATKA
                elif isinstance(e, Message):
                    raise NotImplementedError()

        class PyatkaController(ScreenController):
            def __init__(self):
                ScreenController.__init__(
                    self,
                    text="Выберите пятку:",
                    buttons=[
                        Button("3"),
                        Button("5"),
                        Button("7"),
                        Button("9"),
                        Button("Другой"),
                        Button("Назад"),
                        Button("Отмена"),
                    ],
                )

            def process_event(self, s: StoryState, e: Event):
                if isinstance(e, Action):
                    if e.name == "other":
                        s.state = OrderingState.ENTER_OTHER
                    elif e.name == "cancel":
                        s.state = MainState.IDLE
                    elif e.name == "back":
                        s.state = OrderingState.KABLUK
                    else:
                        pyatka = int(e.name)
                        s.data["pyatka"] = pyatka
                        s.state = OrderingState.COLOR
                elif isinstance(e, Message):
                    raise NotImplementedError()

        class ColorController(ScreenController):
            def __init__(self):
                ScreenController.__init__(
                    self,
                    text="Выберите цвет:",
                    buttons=[
                        Button("Черный"),
                        Button("Бежевый"),
                        Button("Белый"),
                        Button("Другой"),
                        Button("Назад"),
                        Button("Отмена"),
                    ],
                )

            def process_event(self, s: StoryState, e: Event):
                if isinstance(e, Action):
                    if e.name == "other":
                        s.state = OrderingState.ENTER_OTHER
                    elif e.name == "cancel":
                        s.state = MainState.IDLE
                    elif e.name == "back":
                        s.state = OrderingState.PYATKA
                    else:
                        color = e.name
                        s.data["color"] = color
                        s.state = OrderingState.CONFIRM
                elif isinstance(e, Message):
                    raise NotImplementedError()

        class ConfirmController(ScreenController):
            def __init__(self):
                ScreenController.__init__(
                    self,
                    text="Подтвердите заказ:",
                    buttons=[
                        Button("Да, разместить заказ"),
                        Button("Назад"),
                        Button("Отмена"),
                    ],
                )

            def process_event(self, s: StoryState, e: Event):
                if isinstance(e, Action):
                    if e.name == "back":
                        s.state = OrderingState.COLOR
                    elif e.name == "cancel":
                        s.state = MainState.IDLE
                    else:
                        s.state = MainState.IDLE
                elif isinstance(e, Message):
                    raise NotImplementedError()

        class EnterOtherController(ScreenController):
            def __init__(self):
                ScreenController.__init__(
                    self,
                    text="Введите значение:",
                    buttons=[Button("Назад"), Button("Отмена")],
                )

            def process_event(self, s: StoryState, e: Event):
                if isinstance(e, Action):
                    if e.name == "back":
                        s.state = OrderingState.CONFIRM
                    elif e.name == "cancel":
                        s.state = MainState.IDLE
                    else:
                        raise NotImplementedError()
                elif isinstance(e, Message):
                    raise NotImplementedError()

        class ConfirmCancelingController(ScreenController):
            def __init__(self):
                ScreenController.__init__(
                    self,
                    text="Хотите прервать заказ?",
                    buttons=[Button("Да"), Button("Нет")],
                )

            def process_event(self, s: StoryState, e: Event):
                if isinstance(e, Action):
                    if e.name == "back":
                        s.state = OrderingState.CONFIRM
                    elif e.name == "cancel":
                        s.state = MainState.IDLE
                    else:
                        raise NotImplementedError()
                elif isinstance(e, Message):
                    raise NotImplementedError()

        def __init__(self):
            Controller.__init__(self, initial_state=OrderingState.SIZE)
            self.subcontrollers[OrderingState.SIZE] = (
                OrderingController.SizeController()
            )
            self.subcontrollers[OrderingState.KABLUK] = (
                OrderingController.KablukController()
            )
            self.subcontrollers[OrderingState.PYATKA] = (
                OrderingController.PyatkaController()
            )
            self.subcontrollers[OrderingState.COLOR] = (
                OrderingController.ColorController()
            )
            self.subcontrollers[OrderingState.CONFIRM] = (
                OrderingController.ConfirmController()
            )
            self.subcontrollers[OrderingState.ENTER_OTHER] = (
                OrderingController.EnterOtherController()
            )
            self.subcontrollers[OrderingState.CONFIRM_CANCELING] = (
                OrderingController.ConfirmCancelingController()
            )

    root = MainController()

    ses = UserSession(user_id=1, state=StoryState(MainState.IDLE))
    disp = Dispatcher(root=root)

    while True:
        print("=====================================")
        root.render(ses.state)

        try:
            line = input(f"{ses.state.state} >>> ")
        except EOFError:
            break
        except KeyboardInterrupt:
            break

        if line.startswith("#"):
            ev: Union[Action, Message] = Action(1, name=line[1:])
        else:
            ev = Message(1, text=line)

        print("=====================================")
        root.process_event(ses.state, ev)
