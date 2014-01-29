
import json
import urllib
import urllib2
import cookielib
import logging

from utils import AuthData, USER_AGENT

class Reddit(object):
    def __init__(self, auth, sub, dry_run=False):
        self.dry_run = dry_run
        self.sub = sub
        self.logger = logging.getLogger(self.__class__.__name__)

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
        baseurl = 'http://www.reddit.com'
        if params:
            req = urllib2.Request(baseurl + action, urllib.urlencode(params))
        else:
            req = urllib2.Request(baseurl + action)

        response = self.opener.open(req)
        return json.loads(response.read())

    def submit_link(self, link, title, interactive=False):
        if self.dry_run:
            return 'dry-run-reddit-id'

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
                if result['data'].has_key('url'):
                    self.logger.info('Success: {0}'.format(result['data']['url']))
                return result['data']['id']

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

if __name__ == '__main__':
    from sys import argv
    logging.basicConfig(level=logging.DEBUG)

    url = 'http://github.com/mmilata/ektobot' if len(argv) < 1 else argv[1]
    title = 'Ektobot, tool for uploading music archives' if len(argv) < 2 else argv[2]
    sub = 'ektoplazm' if len(argv) < 3 else argv[3]
    auth = AuthData()
    print url, title, sub

    r = Reddit(auth, sub)
    print r.submit_link(url, title, interactive=True)
