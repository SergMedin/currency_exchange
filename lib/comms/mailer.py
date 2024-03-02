from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email_validator import validate_email, EmailNotValidError
import smtplib
from typing import Dict, List
from unittest import TestCase
from typing import Tuple


@dataclass
class EmailAddress:
    original_email: str

    @property
    def addr(self) -> str:
        return str(is_email_valid(self.original_email)["normalized_email"])

    @property
    def is_valid(self) -> bool:
        return bool(is_email_valid(self.original_email)["result"])

    @property
    def obfuscated(self) -> str:
        p = self.addr.split("@", 1)
        username, domain = p[0], p[1] if len(p) > 1 else ""
        obfuscated_username = username[:3] + ".." if len(username) >= 5 else "..."
        obfuscated_domain = ".." + domain[-2:]
        return obfuscated_username + "@" + obfuscated_domain

    def __hash__(self) -> int:
        return hash(self.addr)


class Mailer:
    def __init__(self, allowed_mail_destinations: str | None = None):
        self.allowed_destinations: dict = self.init_allowed_destinations(
            allowed_mail_destinations
        )

    def send_email(self, to: "EmailAddress", text: str):
        raise NotImplementedError()

    def init_allowed_destinations(self, allowed_mail_destinations: str | None) -> dict:
        allowed: dict = {
            "domains": set(),
            "emails": set(),
            "restrictions_active": False,
        }
        if allowed_mail_destinations is not None:
            allowed["restrictions_active"] = True
            destinations = allowed_mail_destinations.lower().split(",")
            for destination in destinations:
                if "@" in destination:
                    allowed["emails"].add(destination)
                else:
                    allowed["domains"].add(destination)
        return allowed

    def is_allowed(self, email: EmailAddress) -> bool:
        if not self.allowed_destinations["restrictions_active"]:
            return True
        if email.addr.lower() in self.allowed_destinations["emails"]:
            return True
        if email.addr.lower().split("@")[1] in self.allowed_destinations["domains"]:
            return True
        return False


def is_email_valid(addr_raw: str) -> Dict[str, str | bool]:
    try:
        valid = validate_email(addr_raw, check_deliverability=False)
        return {"result": True, "normalized_email": valid.normalized}
    except EmailNotValidError as e:
        return {"result": False, "normalized_email": addr_raw}


class MailerMock(Mailer):
    def __init__(self, allowed_mail_destinations: str | None = None):
        super().__init__(allowed_mail_destinations)
        self.sent: Dict[EmailAddress, List[str]] = {}

    def send_email(self, to: EmailAddress, text: str):
        if not self.is_allowed(to):
            raise ValueError(f"Email {to.obfuscated} is not allowed")
        if to not in self.sent:
            self.sent[to] = []
        self.sent[to].append(text)


class MailerReal(Mailer):
    def __init__(
        self,
        server: str,
        port: int,
        user: str,
        app_password: str,
        allowed_mail_destinations: str | None = None,
    ):
        self.server: str = server
        self.port: int = port
        self.user: str = user
        self.password: str = app_password
        super().__init__(allowed_mail_destinations)

    def send_email(self, to: EmailAddress, text: str):
        if not self.is_allowed(to):
            raise ValueError(f"Email {to.obfuscated} is not allowed")
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

        e = EmailAddress("john@gmail.com")
        self.assertTrue(e.is_valid)

        e = EmailAddress("john@gmail.com")
        self.assertEqual("john@gmail.com", e.addr)

    def test_mock(self):
        mm = MailerMock()
        e = EmailAddress("john@gmail.com")
        mm.send_email(e, "hello")
        self.assertEqual(1, len(mm.sent))
        self.assertEqual(1, len(mm.sent[e]))
        self.assertEqual("hello", mm.sent[e][0])

    def test_obfuscation(self):
        self.assertEqual("joh..@..et", EmailAddress("johnson@example.net").obfuscated)
        self.assertEqual("...@..om", EmailAddress("j@x.com").obfuscated)
        self.assertEqual("...@..", EmailAddress("j").obfuscated)
        self.assertEqual("...@..ww", EmailAddress("j@www").obfuscated)
        self.assertEqual("...@..ww", EmailAddress("@www").obfuscated)
        self.assertEqual("...@..om", EmailAddress("@gmail.com").obfuscated)
        self.assertEqual("...@..", EmailAddress("").obfuscated)

    def test_allowed_destinations(self):
        ae1 = EmailAddress("abc@mail.ru")
        ae2 = EmailAddress("abc@mail.ru")
        ae3 = EmailAddress("john@gmail.com")
        fe1 = EmailAddress("jane@mail.ru")
        fe2 = EmailAddress("def@gmail.ru")
        mm = MailerMock("gmail.com,abc@mail.ru")
        self.assertTrue(mm.is_allowed(ae1))
        self.assertTrue(mm.is_allowed(ae2))
        self.assertTrue(mm.is_allowed(ae3))
        self.assertFalse(mm.is_allowed(fe1))
        self.assertFalse(mm.is_allowed(fe2))
        mm.send_email(ae1, "hello")
        self.assertEqual(1, len(mm.sent))
        with self.assertRaises(ValueError) as cm:
            mm.send_email(fe1, "hello")
        self.assertEqual(cm.exception.args[0], "Email ...@..ru is not allowed")
        self.assertEqual(1, len(mm.sent))

    def test_allowed_destinations_inactive(self):
        e1 = EmailAddress("abc@mail.ru")
        e2 = EmailAddress("john@gmail.com")
        mm = MailerMock()
        self.assertTrue(mm.is_allowed(e1))
        self.assertTrue(mm.is_allowed(e2))
