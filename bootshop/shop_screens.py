from typing import Optional, Any
from dataclasses import dataclass
from .stories import (
    Controller,
    Controller,
    Event,
    ButtonAction,
    Message,
    Button,
    OutMessage,
)


class AboutController(Controller):
    def __init__(self, parent: Optional[Controller] = None):
        Controller.__init__(
            self,
            parent,
            text=(
                "В [Название магазина] мы объединяем нашу любовь к аргентинскому "
                "танго с эксклюзивной коллекцией одежды, созданной, чтобы вы "
                "чувствовали себя неотразимо на танцполе. Наша одежда - это не "
                "просто костюмы, это произведения искусства, которые позволяют "
                "танцорам выразить себя в каждом движении."
            ),
            buttons=[Button("Понятно", "ok")],
        )

    def process_event(self, e: Event) -> OutMessage:
        return self.close()


class MainController(Controller):
    def __init__(self):
        Controller.__init__(
            self,
            None,
            text="Привет! Это магазин обуви. Чего желаете?",
            buttons=[Button("Заказать", "order"), Button("О магазине", "about")],
        )
        self._a2c = {
            "order": OrderingController,
            "about": AboutController,
        }

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            return self.show_child(self._a2c[e.name](self))
        raise NotImplementedError()


class EnterOtherController(Controller):
    def __init__(self, parent: "EnterValueController"):
        Controller.__init__(
            self,
            parent=parent,
            text="Введите значение:",
            buttons=[Button("Назад", "back"), Button("Отмена", "cancel")],
        )

    def process_event(self, e: Event) -> OutMessage:
        assert isinstance(self.parent, EnterValueController)
        if isinstance(e, ButtonAction):
            if e.name == "back":
                return self.close()
            elif e.name == "cancel":
                return self.parent.ord.cancel()
            else:
                raise NotImplementedError()
        elif isinstance(e, Message):
            if not e.text.startswith(">"):
                m = self.render()
                m.text = "Значение должно начинаться с '>'"
                return m
            try:
                self.parent.on_other_entered(self._convert(e.text[1:]))
            except ValueError as e:
                m = self.render()
                m.text = str(e)
                return m
        raise NotImplementedError()

    def _convert(self, value: str) -> Any:
        if value.isdigit():
            return int(value)
        raise ValueError("Значение должно быть числом")


class YesNoController(Controller):
    result: Optional[bool] = None

    def __init__(self, parent: Controller, question: str):
        Controller.__init__(
            self,
            text=question,
            buttons=[Button("Да", "yes"), Button("Нет", "no")],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            if e.name in ("yes", "no"):
                self.result = e.name == "yes"
                return self.on_child_finished(self)
        return self.render()


class ConfirmCancelingController(YesNoController):
    def __init__(self, parent: Controller):
        YesNoController.__init__(self, parent, "Хотите прервать заказ?")


class EnterValueController(Controller):
    value: Optional[Any] = None

    @property
    def ord(self) -> "OrderingController":
        assert self.parent
        assert isinstance(self.parent, OrderingController)
        return self.parent

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            if e.name == "other":
                return self.show_child(EnterOtherController(self))
            elif e.name == "cancel":
                return self.cancel()
            else:
                return self._got_value(e.name)
        raise NotImplementedError()

    def _got_value(self, value: Any) -> OutMessage:
        self.value = value
        return self.ord.on_child_finished(self)

    def on_other_entered(self, value: int) -> OutMessage:
        return self._got_value(value)

    def cancel(self) -> OutMessage:
        return self.ord.cancel()


class SizeScreen(EnterValueController):
    def __init__(self, ord: "OrderingController"):
        EnterValueController.__init__(
            self,
            parent=ord,
            text="Выберите размер:",
            buttons=[
                Button("34"),
                Button("35"),
                Button("36"),
                Button("37"),
                Button("38"),
                Button("39"),
                Button("40"),
                Button("Другой", "other"),
                Button("Отмена", "cancel"),
            ],
        )


class KablukController(EnterValueController):
    def __init__(self, ord: "OrderingController"):
        EnterValueController.__init__(
            self,
            parent=ord,
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


class PyatkaController(EnterValueController):
    def __init__(self, ord: "OrderingController"):
        EnterValueController.__init__(
            self,
            parent=ord,
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


class ColorController(EnterValueController):
    def __init__(self, ord: "OrderingController"):
        EnterValueController.__init__(
            self,
            parent=ord,
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


class ConfirmController(Controller):
    def __init__(self):
        Controller.__init__(
            self,
            text="Подтвердите заказ:",
            buttons=[
                Button("Да, разместить заказ"),
                Button("Назад"),
                Button("Отмена"),
            ],
        )

    # def process_event(self, e: Event) -> OutMessage:
    #     if isinstance(e, ButtonAction):
    #         if e.name == "back":
    #             s.state = OrderingState.COLOR
    #         elif e.name == "cancel":
    #             s.state = MainState.IDLE
    #         else:
    #             s.state = MainState.IDLE
    #     elif isinstance(e, Message):
    #         raise NotImplementedError()


class OrderingController(Controller):
    @dataclass
    class OrderDraft:
        size: Optional[int] = None
        kabluk: Optional[int] = None
        pyatka: Optional[int] = None
        color: Optional[str] = None

    def __init__(self, parent: Optional[Controller]):
        Controller.__init__(self, parent)
        self.order = self.OrderDraft()

    def render(self) -> OutMessage:
        if not self.child:
            self.child = SizeScreen(self)
        return self.child.render()

    def on_child_finished(self, child: Controller) -> OutMessage:
        if isinstance(child, SizeScreen):
            self.order.size = child.value
            return self.show_child(KablukController(self))
        elif isinstance(child, KablukController):
            self.order.kabluk = child.value
            return self.show_child(PyatkaController(self))
        elif isinstance(child, PyatkaController):
            self.order.pyatka = child.value
            return self.show_child(ColorController(self))
        elif isinstance(child, ColorController):
            self.order.color = child.value
            return self.show_child(ConfirmController(self))
        elif isinstance(child, ConfirmController):
            pass
        raise ValueError("Unexpected child")

    def cancel(self) -> OutMessage:
        return self.close()
