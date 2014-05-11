
import json
import urllib
import urllib2
import cookielib
import logging

from utils import init_logger, AuthData, Sleeper, USER_AGENT

#TODO: we should consistently either log error and return None or raise an exception

class Reddit(object):
    def __init__(self, auth, sub, dry_run=False):
        init_logger(self)
        self.dry_run = dry_run
        self.sub = sub
        self.sleeper = Sleeper(self.logger)

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
        self.opener.addheaders.append(('x-modhash',  me['data']['modhash']))

    def api_call(self, action, **params): 
        self.sleeper.sleep(2)

        baseurl = 'https://www.reddit.com'
        if params:
            req = urllib2.Request(baseurl + action, urllib.urlencode(params))
        else:
            req = urllib2.Request(baseurl + action)

        response = self.opener.open(req)
        #self.logger.debug('Response: {0}'.format(response.getcode()))
        return json.loads(response.read())

    def submit_link(self, link, title, interactive=False):
        if self.dry_run:
            return ('dry-run-reddit-id', 'http://example.com/foobar/')

        params = {
            'api_type': 'json',
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
        result = self.api_call('/api/comment', api_type='json', parent=thing, text=text)

        try:
            result = result['json']
            if result['errors']:
                self.logger.error('Error: {0}'.format(result['errors']))
                return None
            comment_id = result['data']['things'][0]['data']['id']
            self.logger.debug('Comment posted: {0}'.format(comment_id))
            return comment_id
        except KeyError:
            self.logger.error('Unexpected response: {0}'.format(result))
            return None

def submit_to_reddit(urlstate, sub, auth, interactive=False, dry_run=False):
    r = Reddit(auth, sub, dry_run=dry_run)

    url = ('http://www.youtube.com/watch?v={0}&list={1}'
           .format(urlstate.youtube.videos[0], urlstate.youtube.playlist))

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

    urlstate.reddit.post_id = res[0]
    urlstate.reddit.url = res[1]
    urlstate.reddit.result = 'posted-link'

    comment = u'**[Download the full album from Ektoplazm]({0}).**'.format(urlstate.url)
    if r.submit_comment(urlstate.reddit.post_id, comment):
        urlstate.reddit.result = 'posted-link-and-comment'
        # XXX to be removed after reddit comment count bug is fixed:
        r.submit_comment(urlstate.reddit.post_id, comment)

if __name__ == '__main__':
    import random
    from sys import argv
    logging.basicConfig(level=logging.DEBUG)

    randstr = ''.join([chr(random.choice(range(ord('a'), ord('z')))) for i in range(6)])
    if len(argv) < 2:
        url = 'http://example.com/{0}'.format(randstr)
    else:
        url = argv[1]

    title = 'Ektobot test {0}'.format(randstr) if len(argv) < 3 else argv[2]
    sub = 'ektoplazm' if len(argv) < 4 else argv[3]
    auth = AuthData()

    r = Reddit(auth, sub)
    a =  r.submit_link(url, title, interactive=True)
    if a:
        r.submit_comment(a[0], 'This is a **test** *comment*.')
