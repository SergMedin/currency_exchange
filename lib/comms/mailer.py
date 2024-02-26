from dataclasses import dataclass, field
from email.mime.text import MIMEText
import smtplib
from typing import Dict, List
from unittest import TestCase


class Mailer:
    def send_email(self, to: "EmailAddress", text: str):
        raise NotImplementedError()


def is_email_valid(addr_raw: str) -> bool:
    return "@" in addr_raw  # TODO


@dataclass
class EmailAddress:
    addr: str

    @property
    def is_valid(self) -> bool:
        return is_email_valid(self.addr)

    def __hash__(self) -> int:
        return hash(self.addr)


@dataclass
class MailerMock(Mailer):
    sent: Dict[EmailAddress, List[str]] = field(default_factory=dict)

    def send_email(self, to: EmailAddress, text: str):
        if to not in self.sent:
            self.sent[to] = []
        self.sent[to].append(text)


class MailerReal(Mailer):
    def __init__(self, server: str, port: int, user: str, app_password: str):
        self.server: str = server
        self.port: int = port
        self.user: str = user
        self.password: str = app_password

        
    def send_email(self, to: EmailAddress, text: str):
        msg = MIMEText(text)
        msg["From"] = self.user
        msg["To"] = to.addr
        msg["Subject"] = "Your code for Exhcange Bot"
        server = smtplib.SMTP(self.server, self.port)
        server.starttls()
        server.login(self.user, self.password)
        server.sendmail(self.user, to.addr, msg.as_string())
        server.quit()


class T(TestCase):

    def test_eml(self):
        e = EmailAddress("sdflsdjflksdjf")
        self.assertFalse(e.is_valid)

        e = EmailAddress("john@example.net")
        self.assertTrue(e.is_valid)

        e = EmailAddress("john@example.net")
        self.assertEqual("john@example.net", e.addr)

    def test_mock(self):
        mm = MailerMock()
        e = EmailAddress("john@example.net")
        mm.send_email(e, "hello")
        self.assertEqual(1, len(mm.sent))
        self.assertEqual(1, len(mm.sent[e]))
        self.assertEqual("hello", mm.sent[e][0])
