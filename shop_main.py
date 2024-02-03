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

    root = MainController()
    render_message(root.render())

    while True:
        print("=====================================")

        top_ctl: Controller = root
        while top_ctl.child:
            top_ctl = top_ctl.child

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
            ev: Union[ButtonAction, Message] = ButtonAction(
                1, name=top_ctl.buttons[btn].action
            )
        else:
            ev = Message(1, text=line)

        print("=====================================")
        render_message(top_ctl.process_event(ev))
