
import os
import json
import errno
import os.path
import logging

class UrlState(object):
    def __init__(self, url, j=None):
        if not j:
            j = {}

        self.url = url
        self.youtube = j.get('youtube')

    def to_json(self):
        res = {}
        if self.youtube:
            res['youtube'] = self.youtube

        return res

class State(object):
    def __init__(self, filename):
        if not filename:
            filename = '~/.ektobot/ektobot.json'
        self.filename = os.path.expanduser(filename)

        try:
            with open(self.filename, 'r') as fh:
                j = json.load(fh)
        except IOError as e:
            if e.errno == errno.ENOENT:
                j = { 'version': 1 }
            else:
                raise

        # detect old version
        if 'version' not in j:
            j = self.v0_to_v1(j)

        self.feed = j.get('feed')
        self.urls = {}
        for (url, urlstate) in j.get('urls', {}).iteritems():
            self.urls[url] = UrlState(url, urlstate)

    def to_json(self):
        res = { 'version': 1 }
        res['urls'] = {}

        if self.feed:
            res['feed'] = self.feed

        for (url, urlstate) in self.urls.iteritems():
            res['urls'][url] = urlstate.to_json()

        return res

    def save(self, dry_run=False):
        logger = logging.getLogger('state')
        j = self.to_json()

        if dry_run:
            return

        (directory, base) = os.path.split(self.filename)
        if not os.path.isdir(directory):
            logger.info(u'Creating directory {0}'.format(directory))
            os.makedirs(directory, 0700)

        with open(self.filename, 'w') as fh:
            json.dump(j, fh, indent=2, sort_keys=True)

    @staticmethod
    def v0_to_v1(j):
        res = { 'version': 1 }
        res['feed'] = j['url']

        urls = {}
        for (url, status) in j['albums'].iteritems():
            assert status in ('OK', 'FAIL')
            yts = 'done-unknown-id' if status == 'OK' else 'failed'
            urls[url] = { 'youtube': yts }

        res['urls'] = urls
        return res

    def url(self, url):
        if url in self.urls:
            return self.urls[url]
        else:
            us = UrlState(url)
            self.urls[url] = us
            return us

    def is_processed(self, url):
        return url in self.urls
