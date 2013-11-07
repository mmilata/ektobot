
import sys
import unittest
import StringIO

from ektobot.utils import StdioString
from ektobot.command_line import main

class TestFunctional(unittest.TestCase):
    def assertRunSucceeds(self, args):
        self.assertRaisesRegexp(SystemExit, '0', main, args)

    def assertRunFails(self, args):
        self.assertRaisesRegexp(SystemExit, '^[^0]+$', main, args)

    #Who's gonna test the tester?
    def test_StdioString(self):
        # sys.__stdin__ don't work under nosetests
        orig_in = sys.stdin
        orig_out = sys.stdout
        orig_err = sys.stderr

        with StdioString('foo') as h:
            inp = raw_input()
            print 'a'
            sys.stderr.write('b')

        self.assertEqual(sys.stdin, orig_in)
        self.assertEqual(sys.stdout, orig_out)
        self.assertEqual(sys.stderr, orig_err)
        self.assertEqual(inp, 'foo')
        self.assertEqual(h.stdout, 'a\n')
        self.assertEqual(h.stderr, 'b')

    def test_help(self):
        with StdioString() as h:
            self.assertRunSucceeds(['--help'])
        self.assertIn('usage: ', h.stdout)

        with StdioString() as h:
            self.assertRunFails(['--halp'])

    def test_unpack(self):
        # (bundle an archive)
        # goto temporary dir
        # run unpack
        # check resulting files
        pass
