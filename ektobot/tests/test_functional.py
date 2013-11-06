
import sys
import unittest
import StringIO

from ektobot.command_line import main

class TestFunctional(unittest.TestCase):
    def setUp(self):
        sys.stdin = StringIO.StringIO()
        sys.stdout = StringIO.StringIO()
        sys.stderr = StringIO.StringIO()

    def tearDown(self):
        sys.stdin = sys.__stdin__
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def assertRunSucceeds(self, args):
        self.assertRaisesRegexp(SystemExit, '0', main, args)

    def assertRunFails(self, args):
        self.assertRaisesRegexp(SystemExit, '^[^0]+$', main, args)

    def test_help(self):
        self.assertRunSucceeds(['--help'])
        self.assertIn('usage:', sys.stdout.getvalue())
        self.assertRunFails(['--halp'])

    def test_unpack(self):
        # (bundle an archive)
        # goto temporary dir
        # run unpack
        # check resulting files
        pass
