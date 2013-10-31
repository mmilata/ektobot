
import json
import shutil
import os.path
import getpass
import logging
import tempfile
import contextlib
import subprocess

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

def run(args):
    logger = logging.getLogger('run')
    logger.debug(' '.join(args))

    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(u'Subprocess failed w/ return code {0}, stderr:\n {1}'
                           .format(p.returncode, err))

def write_meta(dirname, meta, dry_run=False, filename='ektobot.json'):
    if dry_run:
        return

    with open(os.path.join(dirname, filename), 'w') as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)

def read_meta(dirname, filename='ektobot.json'):
    with open(os.path.join(dirname, filename), 'r') as fh:
        meta = json.load(fh)
    return meta

def ask_email_password(email=None, passwd=None):
    if not email:
        email = raw_input('youtube login: ')

    if not passwd:
        passwd = getpass.getpass('password: ')

    return (email, passwd)
