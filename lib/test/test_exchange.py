import unittest
from .. import exchange


class T(unittest.TestCase):

    def testSimple(self):
        e = exchange.Exchange(None, None)
        e
