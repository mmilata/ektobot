# coding=utf-8

import unittest

from ektobot.utils import AuthData, StdioString

class TestAuthData(unittest.TestCase):
    def test_simple(self):
        a = AuthData(reddit_login='jogin')

        # pre-set
        with StdioString('foo') as h:
            self.assertEqual(a.reddit_login, 'jogin')

        self.assertEqual(h.stdout, '')
        self.assertEqual(h.stderr, '')

        # ask for login
        with StdioString('foo') as h:
            self.assertEqual(a.sc_login, 'foo')

        self.assertEqual(h.stdout, 'soundcloud login: ')
        self.assertEqual(h.stderr, '')

        # attribute assignment
        with StdioString('foo') as h:
            a.sc_client_id = 'xxx'
            self.assertEqual(a.sc_client_id, 'xxx')

        self.assertEqual(h.stdout, '')
        self.assertEqual(h.stderr, '')

        # XXX do not test attributes containing 'password' substring, it kills
        # the test
