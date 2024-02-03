from typing import Optional, Any, Callable
from dataclasses import dataclass
from .stories import (
    Controller,
    Controller,
    Event,
    ButtonAction,
    Message,
    Button,
    OutMessage,
    YesNoController,
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
    def __init__(
        self,
        parent: "EnterValueController",
        converter: Optional[Callable[[str], Any]] = None,
    ):
        Controller.__init__(
            self,
            parent=parent,
            text="Введите значение:",
            buttons=[Button("Назад", "back"), Button("Отмена", "cancel")],
        )
        if not converter:
            converter = self._convert_to_int
        self._convert = converter

    def process_event(self, e: Event) -> OutMessage:
        assert isinstance(self.parent, EnterValueController)
        if isinstance(e, ButtonAction):
            if e.name == "back":
                return self.close()
            elif e.name == "cancel":
                return self.parent.ord.cancel()
            else:
                raise ValueError(f"Unexpected button {e.name}")
        elif isinstance(e, Message):
            if not e.text.startswith(">"):
                m = self.render()
                m.text = "Значение должно начинаться с '>'"
                return m
            try:
                return self.parent.on_other_entered(self._convert(e.text[1:]))
            except ValueError as e:
                m = self.render()
                m.text = str(e)
                return m
        raise NotImplementedError()

    def _convert_to_int(self, value: str) -> Any:
        if value.isdigit():
            return int(value)
        raise ValueError("Значение должно быть числом")


class EnterValueController(Controller):
    value: Optional[Any] = None

    def __init__(
        self,
        parent: "OrderingController",
        text: str,
        buttons: list[Button],
        btn_other: bool = True,
        confirm_cancel: bool = True,
    ):
        if btn_other:
            buttons += [Button("Другой", "other")]
        buttons += [
            Button("Назад", "back"),
            Button("Отмена", "cancel"),
        ]
        Controller.__init__(self, parent=parent, text=text, buttons=buttons)
        self.confirm_cancel = confirm_cancel

    @property
    def ord(self) -> "OrderingController":
        assert self.parent
        assert isinstance(self.parent, OrderingController)
        return self.parent

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            if e.name == "other":
                return self.show_child(EnterOtherController(self))
            if e.name == "back":
                return self.ord.back(self)
            elif e.name == "cancel":
                return self.cancel()
            else:
                return self._got_value(e.name)
        raise NotImplementedError()

    def _got_value(self, value: Any) -> OutMessage:
        self.value = value
        return self.close()

    def on_other_entered(self, value: int) -> OutMessage:
        return self._got_value(value)

    def cancel(self) -> OutMessage:
        if self.confirm_cancel:
            return self.show_child(YesNoController(self, "Хотите прервать заказ?"))
        return self.ord.cancel()

    def on_child_closed(self, child: Controller) -> OutMessage:
        if isinstance(child, YesNoController):
            if child.result:
                return self.ord.cancel()
            return self.render()
        raise ValueError("Unexpected child")


class SizeScreen(EnterValueController):
    def __init__(self, ord: "OrderingController"):
        EnterValueController.__init__(
            self,
            parent=ord,
            text="Выберите размер:",
            confirm_cancel=False,
            buttons=[
                Button("34"),
                Button("35"),
                Button("36"),
                Button("37"),
                Button("38"),
                Button("39"),
                Button("40"),
            ],
        )


class KablukController(EnterValueController):
    def __init__(self, ord: "OrderingController"):
        EnterValueController.__init__(
            self,
            parent=ord,
            text="Выберите каблук:",
            confirm_cancel=False,
            buttons=[
                Button("3"),
                Button("9"),
                Button("10"),
                Button("85"),
                Button("105"),
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
            ],
        )


class ConfirmController(EnterValueController):
    def __init__(self, ord: "OrderingController"):
        EnterValueController.__init__(
            self,
            parent=ord,
            text=f"Подтвердите заказ {ord.order}:",
            buttons=[
                Button("Да, разместить заказ", "yes"),
            ],
            btn_other=False,
        )


class OrderingController(Controller):
    ORDER_FLOW = [
        (SizeScreen, "size"),
        (KablukController, "kabluk"),
        (PyatkaController, "pyatka"),
        (ColorController, "color"),
        (ConfirmController, None),
    ]

    @dataclass
    class OrderDraft:
        size: Optional[int] = None
        kabluk: Optional[int] = None
        pyatka: Optional[int] = None
        color: Optional[str] = None

    def __init__(self, parent: Optional[Controller]):
        Controller.__init__(self, parent)
        self.order = self.OrderDraft()
        self.child = SizeScreen(self)

    def on_child_closed(self, child: Controller) -> OutMessage:
        _, next, attr = self._get_flow_item(child)
        if attr:
            assert next and isinstance(child, EnterValueController)
            setattr(self.order, attr, child.value)
            return self.show_child(next(self))

        if isinstance(child, ConfirmController):
            if child.value == "yes":
                return OutMessage("Считаем, что заказ сделан") + self.close()
        raise ValueError("Unexpected child")

    def back(self, child: Controller) -> OutMessage:
        prev, _, _ = self._get_flow_item(child)
        if prev:
            return self.show_child(prev(self))
        raise ValueError("Unexpected child")

    def cancel(self) -> OutMessage:
        return self.close()

    def _get_flow_item(
        self, child: Controller
    ) -> tuple[type[Controller] | None, type[Controller] | None, Optional[str]]:
        for i, (cls, attr) in enumerate(self.ORDER_FLOW):
            if isinstance(child, cls):
                prev = self.ORDER_FLOW[i - 1][0] if i > 0 else None
                next = (
                    self.ORDER_FLOW[i + 1][0] if i < len(self.ORDER_FLOW) - 1 else None
                )
                return prev, next, attr
        return None, None, None
