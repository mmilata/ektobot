
import time
import json
import urllib
import urllib2
import cookielib
import logging

from utils import AuthData, USER_AGENT

#TODO: we should consistently either log error and return None or raise an exception

class Reddit(object):
    def __init__(self, auth, sub, dry_run=False):
        self.dry_run = dry_run
        self.sub = sub
        self.logger = logging.getLogger(self.__class__.__name__)
        self.last_request_ts = time.time()

        # prepare
        cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
        self.opener.addheaders = [('user-agent', USER_AGENT)]

        if dry_run:
            return

        # login
        result = self.api_call('/api/login', user=auth.reddit_login, passwd=auth.reddit_password)
        if not any([True for c in cookies if c.name == 'reddit_session']):
            self.logger.error('Login failure, result: {0}'.format(result))
            raise RuntimeError('Login failure')

        self.logger.debug('Successfully logged in')

        me = self.api_call('/api/me.json')
        self.modhash = me['data']['modhash']

    def api_call(self, action, **params): 
        now = time.time()
        tdiff = now - self.last_request_ts
        if tdiff < 2:
            self.logger.debug('Waiting {0} seconds'.format(2-tdiff))
            time.sleep(2-tdiff)

        baseurl = 'http://www.reddit.com'
        if params:
            req = urllib2.Request(baseurl + action, urllib.urlencode(params))
        else:
            req = urllib2.Request(baseurl + action)

        response = self.opener.open(req)
        self.last_request_ts = time.time()
        return json.loads(response.read())

    def submit_link(self, link, title, interactive=False):
        if self.dry_run:
            return ('dry-run-reddit-id', 'http://example.com/foobar/')

        params = {
            'api_type': 'json',
            'uh': self.modhash,
            'kind': 'link',
            'title': title,
            'url': link,
            'sr': self.sub,
        }

        while True:
            result = self.api_call('/api/submit', **params)

            # on success, errors == []
            if not result.has_key('json') or not result['json'].has_key('errors'):
                self.logger.error('Unexpected response: {0}'.format(result))
                return None

            result = result['json']

            if result.has_key('data') and result['data'].has_key('id'):
                post_id = result['data']['id']
                post_url = result['data']['url']
                self.logger.info('Successfully posted: {0}'.format(post_url))
                return (post_id, post_url)

            if len(result['errors']) == 1 and 'BAD_CAPTCHA' in result['errors'][0]:
                if not interactive:
                    break

                captcha_id = result['captcha']
                print('Please solve this captcha: http://www.reddit.com/captcha/{0}'
                      .format(captcha_id))
                captcha = raw_input('captcha (empty to give up)> ')
                if captcha == '':
                    break
                params['iden'] = captcha_id
                params['captcha'] = captcha
                continue
            else:
                self.logger.error('Error: {0}'.format(result['errors']))
                return None

        self.logger.error('Captcha is required')
        return None

    def submit_comment(self, post_id, text):
        thing = 't3_' + post_id
        result = self.api_call('/api/comment', api_type='json', uh=self.modhash,
                               parent=thing, text=text)

        if not result.has_key('json') or not result['json'].has_key('errors'):
            self.logger.error('Unexpected response: {0}'.format(result))
            return False
        if result['json']['errors']:
            self.logger.error('Error: {0}'.format(result['errors']))
            return False
        self.logger.debug('Comment posted')
        return True

def submit_to_reddit(urlstate, sub, auth, interactive=False, dry_run=False):
    r = Reddit(auth, sub, dry_run=dry_run)

    url = ('http://www.youtube.com/watch?v={0}&list={1}'
           .format(urlstate.youtube.playlist, urlstate.youtube.videos[0]))

    if not urlstate.title:
        raise ValueError('Missing title')

    title = urlstate.title
    if urlstate.artist and urlstate.artist != 'VA':
        title = (urlstate.artist + ' - ' + title)
    if urlstate.tags:
        title += (' [' + ', '.join(urlstate.tags) + ']')

    res = r.submit_link(url, title, interactive=interactive)
    if not res:
        raise RuntimeError('Failed to submit link')

    urlstate.reddit.result = 'posted-link'
    urlstate.reddit.post_id = res[0]
    urlstate.reddit.url = res[1]

    comment = u'**[Download the full album from Ektoplazm]({url}).**'.format(urlstate.url)
    if r.submit_comment(urlstate.reddit.post_id, comment):
        urlstate.reddit.result = 'posted-link-and-comment'

if __name__ == '__main__':
    from sys import argv
    logging.basicConfig(level=logging.DEBUG)

    url = 'http://github.com/mmilata/ektobot' if len(argv) < 1 else argv[1]
    title = 'Ektobot, tool for uploading music archives' if len(argv) < 2 else argv[2]
    sub = 'ektoplazm' if len(argv) < 3 else argv[3]
    auth = AuthData()

    r = Reddit(auth, sub)
    a =  r.submit_link(url, title, interactive=True)
    if a:
        r.submit_comment(a[0], 'This is a *test* _comment_.')
