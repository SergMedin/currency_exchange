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

    @property
    def obfuscated(self) -> str:
        p = self.addr.split("@", 1)
        username, domain = p[0], p[1] if len(p) > 1 else ""
        obfuscated_username = username[:3] + ".." if len(username) >= 5 else "..."
        obfuscated_domain = ".." + domain[-2:]
        return obfuscated_username + "@" + obfuscated_domain

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
    def __init__(self, server: str, port: int, user: str, app_password: str, allowed_mails_domains: str | None = None):
        self.server: str = server
        self.port: int = port
        self.user: str = user
        self.password: str = app_password
        self.allowed_mails: dict = self.init_allowed_domains(allowed_mails_domains)

    def init_allowed_domains(self, allowed_mails_domains: str | None):
        restricted: dict = {
            "domains": set(),
            "emails": set(),
        }
        if allowed_mails_domains is not None:
            row_data = allowed_mails_domains.split(",")
            for row in row_data:
                if "@" in row:
                    restricted["emails"].add(row)
                else:
                    restricted["domains"].add(row)
        return restricted
    
    def is_allowed(self, email: EmailAddress) -> bool:
        if email.addr in self.allowed_mails["emails"]:
            return True
        if email.addr.split("@")[1] in self.allowed_mails["domains"]:
            return True
        return False

    def send_email(self, to: EmailAddress, text: str):
        if not self.is_allowed(to):
            raise ValueError(f"Email {to.addr} is not allowed to send")
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

    def test_obfuscation(self):
        self.assertEqual("joh..@..et", EmailAddress("johnson@example.net").obfuscated)
        self.assertEqual("...@..om", EmailAddress("j@x.com").obfuscated)
        self.assertEqual("...@..", EmailAddress("j").obfuscated)
        self.assertEqual("...@..ww", EmailAddress("j@www").obfuscated)
        self.assertEqual("...@..ww", EmailAddress("@www").obfuscated)
        self.assertEqual("...@..om", EmailAddress("@gmail.com").obfuscated)
        self.assertEqual("...@..", EmailAddress("").obfuscated)
