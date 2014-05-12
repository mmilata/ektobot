
import re
import cgi
import urllib
import urllib2
import logging
import os.path
import urlparse
import contextlib
import BeautifulSoup

from utils import init_logger, USER_AGENT

class License(object):
    def __init__(self, url):
        self.url = url
        self.name = None
        self.nc = None
        self.nd = None
        self.sa = None

        m = re.match(r'http://creativecommons\.org/licenses/([^/]+)/([^/]+)/?$', url)
        if m:
            self.name = 'cc'
            (lic, ver) = (m.group(1), m.group(2))

            self.nc = ('-nc' in lic)
            self.nd = ('-nd' in lic)
            self.sa = ('-sa' in lic)

    def __str__(self):
        return ('License(url={0}, type={1}, nc={2}, nd={3}, sa={4})'
                .format(self.url, self.name, self.nc, self.nd, self.sa))

class Source(object):
    def __init__(self, page_url, html_string=None):
        init_logger(self)
        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('user-agent', USER_AGENT)]

        if html_string:
            self.html = html_string
        else:
            assert page_url
            self.logger.debug(u'Fetching {0}'.format(page_url))
            self.html = self.opener.open(page_url).read()

        self.soup = BeautifulSoup.BeautifulSoup(self.html)

    @property
    def archive_link(self):
        return self.get_archive_link()

    @property
    def tags(self):
        return set(self.get_tags())

    @property
    def license(self):
        url = self.get_license_link()
        if url:
            return License(url)

    def get_license_link(self):
        return None

    def get_tags(self):
        return set()

    def get_archive_link(self):
        raise NotImplementedError('archive_link')

    def _url_file_name(self, fh):
        try:
            _, params = cgi.parse_header(fh.headers['content-disposition'])
            return params['filename']
        except KeyError:
            pass # header not found, fall back on parsing url

        url = urlparse.urlparse(fh.geturl())
        path = urllib.unquote_plus(url.path)
        fname = path.rsplit('/', 1)[-1]
        self.logger.debug(u'Content-disposition missing, fallback file name {0}'.format(fname))
        return fname

    def download_archive(self, directory):
        with contextlib.closing(self.opener.open(self.archive_link)) as inf:
            chunk_size = 8192
            total_size = int(inf.headers['content-length'])
            read = 0
            nsteps = 10
            step = int(total_size / nsteps)

            archive = os.path.join(directory, self._url_file_name(inf))

            with open(archive, 'w') as outf:
                self.logger.info(u'Download size {0}M, destination {1}'
                                 .format(total_size/1024/1024, archive))

                while True:
                    chunk = inf.read(chunk_size)
                    if not chunk:
                        break
                    outf.write(chunk)

                    read += len(chunk)
                    if read / step > (read-len(chunk)) / step:
                        self.logger.debug(u'{0} %'.format(int(100.0*read/step/nsteps)))

        self.logger.debug('Download complete')
        return archive

class Ektoplazm(Source):
    def get_archive_link(self):
        h_mp3_link = self.soup('a', text='MP3 Download')
        if len(h_mp3_link) != 1:
            raise SyntaxError('MP3 Download links: {0}'
                              .format(len(h_mp3_link)))

        mp3_link = h_mp3_link[0].parent['href']
        self.logger.debug(u'Found archive url: {0}'.format(mp3_link))
        return mp3_link

    def get_tags(self):
        # <span class="style">
        h_tag_span = self.soup('span', 'style')
        if len(h_tag_span) != 1:
            self.logger.warning(u'Found {0} tag spans, ignoring'.format(len(h_tag_span)))
            return []

        h_tags = h_tag_span[0]('a')
        if len(h_tag_span) <= 0:
            raise SyntaxError('No tags')

        return map(lambda h: h.string, h_tags)

    def get_license_link(self):
        h_cc_link = self.soup('a', href=re.compile('http[s]?://(www.)?creativecommons.org/'))
        if len(h_cc_link) != 1:
            raise SyntaxError('Found {0} license links'
                              .format(len(h_cc_link)))

        license_link = h_cc_link[0]['href']
        self.logger.debug(u'License: {0}'.format(license_link))
        return license_link


if __name__ == '__main__':
    import sys
    from utils import TemporaryDir
    logging.basicConfig(level=logging.DEBUG)
    a = Ektoplazm(sys.argv[1])
    print a.archive_link
    print a.tags
    print a.license
    with TemporaryDir('ektobot.source') as tmpdir:
        print a.download_archive(tmpdir)
