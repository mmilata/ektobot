
import sys
import json
import time
import shutil
import os.path
import getpass
import logging
import StringIO
import tempfile
import contextlib
import subprocess

USER_AGENT = 'ektobot-0'

@contextlib.contextmanager
def TemporaryDir(name='tmp', keep=False):
    logger = logging.getLogger('tmpdir')
    dname = tempfile.mkdtemp(prefix=name+'.')
    try:
        logger.debug('Created temporary directory {0}'.format(dname))
        yield dname
    finally:
        if not keep:
            logger.debug('Deleting temporary directory {0}'.format(dname))
            shutil.rmtree(dname)

@contextlib.contextmanager
def StdioString(init_stdin=""):
    class Handle(object):
        def __init__(self):
            self.stdin = sys.stdin = StringIO.StringIO(init_stdin)
            self.stdout = sys.stdout = StringIO.StringIO()
            self.stderr = sys.stderr = StringIO.StringIO()

        def getvalues(self):
            self.stdin = sys.stdin.getvalue()
            self.stdout = sys.stdout.getvalue()
            self.stderr = sys.stderr.getvalue()

    try:
        (orig_in, orig_out, orig_err) = (sys.stdin, sys.stdout, sys.stderr)
        h = Handle()
        yield h
        h.getvalues()
    finally:
        sys.stdin = orig_in
        sys.stdout = orig_out
        sys.stderr = orig_err

class AuthData(object):
    def __init__(self, **kwargs):
        self.fields = {
            'yt_login': 'youtube login',
            'yt_password': 'youtube password',
            'sc_login': 'soundcloud login',
            'sc_password': 'soundcloud password',
            'sc_client_id': 'soundcloud client id',
            'sc_client_secret': 'soundcloud client secret',
            'reddit_login': 'reddit login',
            'reddit_password': 'reddit password',
        }

        for (k, v) in kwargs.items():
            assert k in self.fields
            if v:
                self.__dict__[k] = v

    def __getattr__(self, attr):
        if attr in self.fields:
            if 'password' in attr:
                v = getpass.getpass(self.fields[attr] + ': ')
            else:
                v = raw_input(self.fields[attr] + ': ')
            self.__dict__[attr] = v
            return v
        else:
            raise AttributeError(attr)

class Sleeper(object):
    def __init__(self, logger=None):
        self.logger = logger
        self.last_request_ts = 0.0

    def sleep(self, seconds_from_last):
        tdiff = time.time() - self.last_request_ts
        if tdiff < seconds_from_last:
            wait_seconds = seconds_from_last - tdiff
            if self.logger:
                self.logger.debug('Waiting {0} seconds'.format(wait_seconds))
            time.sleep(wait_seconds)

        self.last_request_ts = time.time()

def init_logger(self):
    self.logger = logging.getLogger(self.__class__.__name__.lower())

def run(args):
    debugstr = args[0] + ' ' + ' '.join(map("'{0}'".format, args[1:]))
    logger = logging.getLogger('run')
    logger.debug(debugstr)

    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(u'Subprocess failed w/ return code {0}, stderr:\n {1}'
                           .format(p.returncode, err))

def write_dirmeta(dirname, meta, dry_run=False, filename='ektobot.json'):
    if dry_run:
        return

    with open(os.path.join(dirname, filename), 'w') as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)

def read_dirmeta(dirname, filename='ektobot.json'):
    with open(os.path.join(dirname, filename), 'r') as fh:
        meta = json.load(fh)
    return meta

def load_config(filename):
    res = {}

    with open(filename, 'r') as fh:
        cfgstr = fh.read()

    section = None
    for lineno, line in enumerate(cfgstr.splitlines()):
        line = line.strip()

        if line == '' or line.startswith('#'):
            pass

        elif line.startswith('[') and line.endswith(']'):
            section = line[1:][:-1].strip()
            if section not in res:
                res[section] = {}

        elif '=' in line:
            (k, v) = line.split('=', 2)
            k = k.strip()
            v = v.strip()

            if section is None:
                raise SyntaxError('{0}: missing first section'.format(filename))
            res[section][k] = v

        else:
            raise SyntaxError('{0}: malformed line {1}'.format(filename, lineno))

    return res
