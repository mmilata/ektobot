
import os
import json
import errno
import os.path
import logging

CURRENT_VERSION = 2

class YouTubeState(object):
    def __init__(self, j=None):
        if not j:
            j = {}

        self.result = j.get('result')
        self.playlist = j.get('playlist')
        self.videos = j.get('videos')

    def to_json(self):
        res = {}

        if self.result:
            res['result'] = self.result
        if self.playlist:
            res['playlist'] = self.playlist
        if self.videos:
            res['videos'] = self.videos

        return res

class UrlState(object):
    def __init__(self, url, j=None):
        if not j:
            j = {}

        self.url = url
        self.youtube = YouTubeState(j.get('youtube'))
        self.license = j.get('license')
        self.tags = set(j.get('tags', []))

    def to_json(self):
        res = {}
        if self.youtube:
            res['youtube'] = self.youtube.to_json()
        if self.license:
            res['license'] = self.license
        if self.tags:
            res['tags'] = list(self.tags)

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
                j = { 'version': CURRENT_VERSION }
            else:
                raise

        # detect old version
        if 'version' not in j:
            j = self.v0_to_v1(j)
        if j['version'] == 1:
            j = self.v1_to_v2(j)

        if j['version'] != CURRENT_VERSION:
            raise RuntimeError('Cannot handle version {0} of state file'.format(j['version']))

        self.feed = j.get('feed')
        self.urls = {}
        for (url, urlstate) in j.get('urls', {}).iteritems():
            self.urls[url] = UrlState(url, urlstate)

    def to_json(self):
        res = { 'version': CURRENT_VERSION }
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

        directory = os.path.dirname(self.filename)
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

    @staticmethod
    def v1_to_v2(j):
        j['version'] = 2
        for urlstate in j['urls'].itervalues():
            old_yt = urlstate['youtube']
            assert old_yt in ['done-unknown-id', 'failed']
            if old_yt == 'done-unknown-id':
                new_yt = { 'result': 'done' }
            else:
                new_yt = { 'result': 'failed' }
            urlstate['youtube'] = new_yt

        return j

    def url(self, url):
        if url in self.urls:
            return self.urls[url]
        else:
            us = UrlState(url)
            self.urls[url] = us
            return us

    def is_processed(self, url):
        return url in self.urls
