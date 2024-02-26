from dataclasses import dataclass, field
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
