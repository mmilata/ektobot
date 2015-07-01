# coding=utf-8

import unittest

from ektobot.utils import AuthData, StdioString
from ektobot.video_convert import find_cover_in_list

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

class TestUtils(unittest.TestCase):
    def test_find_cover(self):
        choices = [
            ['a.png', 'folder.jpg'],
            ['a.png', 'b.png', 'folder.jpg'],
            ['folder.jpg'],
            ['foo image 1.jpg', 'asdf', 'folder.jpg'],
            ['foo image 3.jpg', 'asdf', 'folder.jpg'],
            ['a', 'foo: front.png', 'b'],
        ]

        right = [
            'a.png',
            'folder.jpg',
            'folder.jpg',
            'foo image 1.jpg',
            'folder.jpg',
            'foo: front.png',
        ]

        for files, rightfile in zip(choices, right):
            chosen = find_cover_in_list(files)
            assert chosen == rightfile
