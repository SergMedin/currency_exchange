import logging
from lib.botlib.stories import (
    Button,
    Controller,
    Event,
    OutMessage,
    ButtonAction,
    Message,
)
from lib.dialogs.base import ExchgController
from lib.dialogs.place_order import CreateOrder
from lib.rep_sys.rep_sys import RepSysUserId
from lib.rep_sys.email_auth import EmlAuthState, TooManyAttemptsOrExpiredError


class AuthMain(ExchgController):

    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Not supported",
        )
        if self.session.email_auth is None:
            self.session.email_auth = self.session.app.get_email_authenticator(
                RepSysUserId(self.session.user_id)
            )

    def render(self) -> OutMessage:
        if not self.is_authenticated:
            assert self.session.email_auth
            if self.session.email_auth.state == EmlAuthState.WAIT_EMAIL:
                return self.show_child(AuthEnterEmail(self))
            elif self.session.email_auth.state == EmlAuthState.WAIT_CODE:
                return self.show_child(AuthEnterCode(self))
            else:
                raise ValueError(
                    f"Unknown email auth state: {self.session.email_auth.state}"
                )
        else:
            return self.show_child(Authenticated(self))


class AuthEnterEmail(ExchgController):

    def __init__(self, parent: AuthMain):
        super().__init__(
            parent=parent,
            text="Введите ваш email:",
            buttons=[
                [Button("Другой способ авторизации", "alternative")],
                [Button("Отмена", "cancel")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            if e.name == "cancel":
                assert self.parent
                res = self.parent.close()
            elif e.name == "alternative":
                assert self.parent
                res = self.show_child(AuthAlternative(self.parent))
            else:
                logging.error(f"Unknown button action: {e.name}")
                res = self.render()
            return self.edit_last(e, res)
        elif isinstance(e, Message):
            assert self.session.email_auth
            wannabe_uid = RepSysUserId.from_email(e.text)
            wannabe_uid.telegram_user_id = e.user_id
            if not self.session.rep_sys.is_id_consistent(wannabe_uid):
                return OutMessage("Неверный email") + self.render()

            try:
                self.session.email_auth.send_email(e.text)
            except ValueError as ex:
                return OutMessage(str(ex)) + self.render()
            return self.close()
        else:
            return OutMessage(f"Unknown event {e}") + self.render()


class AuthEnterCode(ExchgController):

    def __init__(self, parent: AuthMain):
        super().__init__(
            parent=parent,
            text="Введите код:",
            buttons=[
                [Button("Отправить заново", "resend")],
                [Button("Отмена", "cancel")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            if e.name == "cancel":
                assert self.parent
                res = self.parent.close()
            elif e.name == "resend":
                assert self.session.email_auth
                self.session.email_auth.reset()
                res = self.close()
            else:
                logging.error(f"Unknown button action: {e.name}")
                res = self.render()
            return self.edit_last(e, res)
        elif isinstance(e, Message):
            assert self.session.email_auth
            try:
                if self.session.email_auth.is_code_valid(e.text):
                    uid = self.session.email_auth.user_id
                    self.session.rep_sys.set_authenticity(uid, True)
                    self.session.email_auth.delete()
                    self.session.email_auth = None
                    return self.close()
                else:
                    return OutMessage("Неверный код") + self.render()
            except TooManyAttemptsOrExpiredError as ex:
                return (
                    OutMessage("Исчерпан лимит количества попыток или времени")
                    + self.close()
                )
            except Exception as ex:
                return OutMessage(str(ex)) + self.render()
        else:
            return OutMessage(f"Unknown event {e}") + self.render()


class Authenticated(ExchgController):

    def __init__(self, parent: AuthMain):
        super().__init__(
            parent=parent,
            text="Вы успешно авторизованы",
            buttons=[
                [Button("Теперь создать заявку", "create_order")],
                [Button("Хорошо", "ok")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        if isinstance(e, ButtonAction):
            if e.name == "ok":
                assert self.parent
                res = self.parent.close()
            elif e.name == "create_order":
                assert self.parent and self.parent.parent
                res = self.show_child(CreateOrder(self.parent.parent))
            else:
                logging.error(f"Unknown button action: {e.name}")
                res = self.render()
            return self.edit_last(e, res)
        else:
            return OutMessage(f"Unknown event {e}") + self.render()


class AuthAlternative(ExchgController):

    def __init__(self, parent: Controller):
        super().__init__(
            parent=parent,
            text="Напишите Сереге в телеграмме и он вас авторизует",
            buttons=[
                [Button("Понятно", "ok")],
            ],
        )

    def process_event(self, e: Event) -> OutMessage:
        assert self.parent and self.parent.parent
        if isinstance(e, ButtonAction):
            if e.name == "ok":
                res = self.parent.parent.close()
            return self.edit_last(e, res)
        else:
            return self.parent.parent.close()
