# coding=utf-8

import shutil
import os.path
import unittest

from ektobot.utils import load_config, TemporaryDir

KEEP = False
CFGNAME = 'config'

ex_a_1 = '[main]\na = b\nfoo=bar\n'
ex_a_2 = ' [ main ] \n a = b \nfoo=bar'
ex_a_3 = '[main]\na = b\n foo=bar\n x = y'
ex_a_4 = '#comment\n[main]\na = b\nfoo=bar\n'
ex_a_5 = '[main]\n#comment\na = b\nfoo=bar\n'
ex_a_6 = '\n\n[main]\na = b\nfoo=bar\n#cmt\n'
ex_a_7 = '#c\n[main]\n#c\na = b\n#c\n\nfoo=bar\n'

ex_fail_1 = 'a=b'
ex_fail_2 = 'xzzz=hhhhhHb\n[majka]\npastika = fuj'

ex_uni = '[oddělení]\nklíč = žluťoučká hodnota'


class TestConfig(unittest.TestCase):
    def setUp(self):
        with TemporaryDir('ektobot.test_config', keep=KEEP) as tmpdir:
            pass
        self.tmpdir = tmpdir
        self.cfgfile = os.path.join(tmpdir, CFGNAME)

    def tearDown(self):
        if not KEEP:
            shutil.rmtree(self.tmpdir)

    def prepare_file(self, contents):
        with open(self.cfgfile, 'w') as fh:
            fh.write(contents)

    def test_simple(self):
        for ex in (ex_a_1, ex_a_2, ex_a_3, ex_a_4, ex_a_5, ex_a_6, ex_a_7):
            self.prepare_file(ex)

            c = load_config(self.cfgfile)
            self.assertIsInstance(c, dict)
            self.assertIn('main', c)
            self.assertIsInstance(c['main'], dict)
            self.assertIn('a', c['main'])
            self.assertIn('foo', c['main'])
            self.assertEqual(c['main']['a'], 'b')
            self.assertEqual(c['main']['foo'], 'bar')

    def test_fail(self):
        for ex in (ex_fail_1, ex_fail_2):
            self.prepare_file(ex)

            with self.assertRaises(SyntaxError):
                c = load_config(self.cfgfile)

    def test_uni(self):
        self.prepare_file(ex_uni)
        c = load_config(self.cfgfile)
        self.assertIn('oddělení', c)
        self.assertIn('klíč', c['oddělení'])
        self.assertEqual(c['oddělení']['klíč'], 'žluťoučká hodnota')
