# coding=utf-8

import json
import stat
import shutil
import os.path
import unittest

from ektobot.utils import TemporaryDir
from ektobot.state import State, UrlState, YouTubeState

KEEP = False
STATENAME = 'ektobot.json'
URL1 = 'http://example.com'
URL2 = 'http://localhost'
URL3 = 'http://127.0.0.1'
LICENSE_URL = 'http://creativecommons.org/licenses/by-nc-sa/3.0/'

ex_v2_s1 = {
    'version': 2,
    'feed': URL1,
    'urls': {
        URL2: {'youtube': {'result': 'done'}}
    }
}
ex_v2_s2 = {
    'version': 2,
    'feed': URL1,
    'urls': {
        URL2: {'youtube': {'result': 'done'}},
        URL3: {'youtube': {'result': 'failed'}},
    }
}
ex_v2_s3 = {
    'version': 2,
    'feed': URL1,
    'urls': {
        URL2: {
            'youtube': {
                'result': 'done',
                'playlist': 'PLjAN2Ez8EzGrUMIevZzvV894eQiEA9TnY',
                'videos': ['JV9XAsbqgHY', 'r6XRC13Bskk']
            },
            'tags': ['Grindcore', 'Prog Death'],
            'license': LICENSE_URL,
        },
        URL3: {'youtube': {'result': 'failed'}}
    }
}
ex_v1_s1 = {
    'version': 1,
    'feed': URL1,
    'urls': {
        URL2: {'youtube': 'done-unknown-id'}
    }
}
ex_v1_s2 = {
    'version': 1,
    'feed': URL1,
    'urls': {
        URL2: {'youtube': 'done-unknown-id'},
        URL3: {'youtube': 'failed'}
    }
}
ex_v0 = {
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
        self.prepare_file(ex_v2_s1)
        orig_contents = open(self.statefile, 'r').read()
        state = State(self.statefile)

        self.assertEqual(state.feed, URL1)
        self.assertIsInstance(state.urls, dict)
        self.assertIn(URL2, state.urls)
        self.assertIsInstance(state.urls[URL2], UrlState)

        urlstate = state.urls[URL2]
        self.assertEqual(urlstate.url, URL2)

        self.assertIsInstance(urlstate.youtube, YouTubeState)
        self.assertEqual(urlstate.youtube.result, 'done')
        self.assertEqual(state.to_json(), ex_v2_s1)

        state.url(URL3).youtube.result = 'failed'
        self.assertEqual(state.to_json(), ex_v2_s2)

        state.url(URL2).youtube.playlist = 'PLjAN2Ez8EzGrUMIevZzvV894eQiEA9TnY'
        state.url(URL2).youtube.videos = ['JV9XAsbqgHY', 'r6XRC13Bskk']
        state.url(URL2).tags = ['Grindcore', 'Prog Death']
        state.url(URL2).license = LICENSE_URL
        self.assertEqual(state.to_json(), ex_v2_s3)

        state.save()
        new_contents = open(self.statefile, 'r').read()
        self.assertNotEqual(orig_contents, new_contents)

    def test_v0_to_v2(self):
        self.prepare_file(ex_v0)
        state = State(self.statefile)

        self.assertEqual(state.feed, URL1)
        self.assertEqual(state.to_json(), ex_v2_s1)

    def test_v1_to_v2(self):
        self.prepare_file(ex_v1_s1)
        state = State(self.statefile)
        self.assertEqual(state.to_json(), ex_v2_s1)

        self.prepare_file(ex_v1_s2)
        state = State(self.statefile)
        self.assertEqual(state.to_json(), ex_v2_s2)

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
