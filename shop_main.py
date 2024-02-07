from bootshop.shop_screens import (
    MainController,
    Controller,
    OutMessage,
    ButtonAction,
    Message,
)
from typing import Union


if __name__ == "__main__":

    def render_message(m: OutMessage):
        print(m.text)
        if m.buttons:
            for i, b in enumerate(m.buttons, start=1):
                print(f"{i}. {b.text}")
            print("Введите номер кнопки:")
        if m.next:
            render_message(m.next)

    root = MainController()
    render_message(root.render())

    while True:
        print("=====================================")

        stack: list[Controller] = [root]
        while stack[-1].child is not None:
            stack.append(stack[-1].child)
        top_ctl = stack[-1]

        print("Stack: [", " > ".join(c.__class__.__name__ for c in stack), "]")
        try:
            line = input(f" >>> ")
        except EOFError:
            break
        except KeyboardInterrupt:
            break

        if line.isdigit():
            btn = int(line) - 1
            if top_ctl.buttons is None:
                raise ValueError("No buttons")
            if btn < 0 or btn >= len(top_ctl.buttons):
                raise ValueError(
                    f"Invalid button number. Buttons: {top_ctl.buttons}, top_ctl: {top_ctl}"
                )
            ev: Union[ButtonAction, Message] = ButtonAction(
                1, name=top_ctl.buttons[btn].action
            )
        else:
            ev = Message(1, text=line)

        print("=====================================")
        render_message(top_ctl.process_event(ev))
