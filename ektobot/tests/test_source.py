# coding=utf-8

import shutil
import os.path
import unittest

from ektobot.source import Ektoplazm

KEEP = False

zip_url1 = 'http://www.ektoplazm.com/files/Globular%20-%20Magnitudes%20Of%20Order%20-%202013%20-%20MP3.zip'
cc_by_nc_sa_3_url = 'http://creativecommons.org/licenses/by-nc-sa/3.0/'


class TestSource(unittest.TestCase):
    def load_html(self, filename):
        html_file = os.path.dirname(__file__)
        html_file = os.path.join(html_file, 'data', filename)

        with open(html_file, 'r') as fh:
            self.html = fh.read()

        return self.html

    def test_ektoplazm0(self):
        e = Ektoplazm(None, html_string='invalid html')

        self.assertEqual(e.tags, set())

        with self.assertRaises(SyntaxError):
            e.archive_link

        with self.assertRaises(SyntaxError):
            e.license

    def test_ektoplazm1(self):
        self.load_html('ektoplazm1.html')
        e = Ektoplazm(None, html_string=self.html)

        self.assertEqual(e.tags, set(['Downtempo', 'Psy Dub']))
        self.assertEqual(e.archive_link, zip_url1)

        license = e.license
        self.assertEqual(license.url, cc_by_nc_sa_3_url)
        self.assertEqual(license.name, 'cc')
        self.assertTrue(license.nc)
        self.assertFalse(license.nd)
        self.assertTrue(license.sa)
