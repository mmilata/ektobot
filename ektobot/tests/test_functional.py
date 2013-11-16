
import os
import sys
import json
import shutil
import os.path
import unittest
import StringIO

from ektobot.utils import StdioString, TemporaryDir
from ektobot.command_line import main

KEEP = False
STATENAME = 'state.json'
SONGNAME = '01 - Test artist - Test song.mp3'
ZIPNAME = 'Test artist - Test album - 2013 - MP3.zip'
DIRNAME = 'Test_artist_-_Test_album'
COVERNAME = 'folder.jpg'

class TestFunctional(unittest.TestCase):
    def assertRunSucceeds(self, args):
        try:
            main(args)
        except SystemExit as e:
            if (e.code != 0):
                raise

    def assertRunFails(self, args):
        try:
            main(args)
        except SystemExit as e:
            if (e.code == 0):
                raise

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

    def test_commands(self):
        with TemporaryDir('ektobot.test_unpack', keep=KEEP) as tmpdir:
            os.chdir(tmpdir)
            src = os.path.dirname(__file__)
            src = os.path.join(src, 'data', ZIPNAME)
            shutil.copy(src, '.')

            with StdioString() as h:
                self.assertRunSucceeds(['unpack', ZIPNAME])

            self.assertTrue(os.path.isdir(os.path.join(tmpdir, DIRNAME)))
            self.assertTrue(os.path.isfile(os.path.join(DIRNAME, SONGNAME)))

            # XXX ffmpeg segfaults on Fedora 19
            #with StdioString() as h:
            #    self.assertRunSucceeds(['videos', DIRNAME])

    def test_state_file(self):
        with TemporaryDir('ektobot.test_state_file', keep=KEEP) as tmpdir:
            statefile = os.path.join(tmpdir, STATENAME)
            self.assertFalse(os.path.isfile(statefile))
            with StdioString() as h:
                self.assertRunSucceeds(['--state-file', statefile, 'set-url', 'http://example.com'])
            self.assertTrue(os.path.isfile(statefile))

            meta = json.load(open(statefile, 'r'))
            self.assertIsInstance(meta, dict)
            self.assertIn('feed', meta)
            rhs = { 'version': 1, 'feed': 'http://example.com', 'urls': {} }
            self.assertEqual(meta, rhs)


if __name__ == '__main__':
    from ektobot.utils import run
    import logging
    logging.basicConfig(level=logging.DEBUG)

    run(['sox', '-n', 'sound.wav', 'synth', '3', 'sine', '300-3300'])
    run(['lame',
         '--tt', 'Test song',
         '--ta', 'Test artist',
         '--tl', 'Test album',
         '--ty', '2013',
         '--tn', '1/1',
         'sound.wav', SONGNAME])
    run(['convert', '-size', '100x100', 'canvas:green', COVERNAME])
    run(['zip', ZIPNAME, SONGNAME, COVERNAME])
