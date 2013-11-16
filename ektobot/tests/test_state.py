# coding=utf-8

import json
import stat
import shutil
import os.path
import unittest

from ektobot.utils import TemporaryDir
from ektobot.state import State, UrlState

KEEP = False
STATENAME = 'ektobot.json'
URL1 = 'http://example.com'
URL2 = 'http://localhost'
URL3 = 'http://127.0.0.1'

ex_s_1 = {
    'version': 1,
    'feed': URL1,
    'urls': {
        URL2: {'youtube': 'done-unknown-id'}
    }
}
ex_s_2 = {
    'version': 1,
    'feed': URL1,
    'urls': {
        URL2: {'youtube': 'done-unknown-id'},
        URL3: {'youtube': 'failed'}
    }
}
ex_old = {
    'url': URL1,
    'albums': { URL2: 'OK' }
}


class TestState(unittest.TestCase):
    def setUp(self):
        with TemporaryDir('ektobot.test_state', keep=True) as tmpdir:
            pass
        self.tmpdir = tmpdir
        self.statefile = os.path.join(tmpdir, STATENAME)

    def tearDown(self):
        if not KEEP:
            shutil.rmtree(self.tmpdir)

    def prepare_file(self, j):
        with open(self.statefile, 'w') as fh:
            json.dump(j, fh, indent=2, sort_keys=True)

    def test_simple(self):
        self.prepare_file(ex_s_1)
        orig_contents = open(self.statefile, 'r').read()
        state = State(self.statefile)

        self.assertEqual(state.feed, URL1)
        self.assertIsInstance(state.urls, dict)
        self.assertIn(URL2, state.urls)
        self.assertIsInstance(state.urls[URL2], UrlState)

        urlstate = state.urls[URL2]

        self.assertEqual(urlstate.url, URL2)
        self.assertEqual(urlstate.youtube, 'done-unknown-id')

        self.assertEqual(state.to_json(), ex_s_1)

        state.url(URL3).youtube = 'failed'
        self.assertEqual(state.to_json(), ex_s_2)

        state.save()
        new_contents = open(self.statefile, 'r').read()
        self.assertNotEqual(orig_contents, new_contents)
        self.assertNotEqual(len(orig_contents), len(new_contents))

    def test_v0_to_v1(self):
        self.prepare_file(ex_old)
        state = State(self.statefile)

        self.assertEqual(state.feed, URL1)
        self.assertEqual(state.to_json(), ex_s_1)

    def test_create(self):
        dotdir = os.path.join(self.tmpdir, '.ektobot')
        statefile = os.path.join(dotdir, STATENAME)
        self.assertFalse(os.path.isdir(dotdir))
        self.assertFalse(os.path.isfile(statefile))

        state = State(statefile)
        state.feed = URL1
        state.save()

        self.assertTrue(os.path.isdir(dotdir))
        self.assertTrue(os.path.isfile(statefile))
        self.assertEqual(stat.S_IMODE(os.stat(dotdir).st_mode), 0700)

        state = State(statefile)
        self.assertEqual(state.feed, URL1)
