
import re
import cgi
import time
import urllib
import urllib2
import os.path
import logging
import urlparse
import contextlib

from unpack import unpack
from utils import read_meta, ask_email_password, TemporaryDir, USER_AGENT
from video_convert import videos
from youtube import ytupload

def watch_rss(meta, dry_run, email=None, passwd=None, keep=False, sleep_interval=30*60):
    import feedparser

    logger = logging.getLogger('rss')

    def mp3_link(e):
        for l in e.links:
            if 'rel' in l and l.rel == 'enclosure' and 'title' in l and l.title == 'MP3 Download':
                return l.href
        return None

    (email, passwd) = ask_email_password(email, passwd)

    while True:
        feed = feedparser.parse(meta.feed) # XXX may throw exception

        for entry in feed.entries:
            if entry.link not in meta.urls:
                process_url(meta, entry.link, mp3_link(entry), dry_run, email, passwd,
                            keep=keep)
        try:
            time.sleep(sleep_interval)
        except KeyboardInterrupt:
            logger.info('User requested exit')
            break

def process_list(meta, listfile, dry_run, email=None, passwd=None, keep=False, retry=False):
    logger = logging.getLogger('list')

    urls = read_meta(listfile) # not a state file
    (email, passwd) = ask_email_password(email, passwd)

    for url in urls:
        if url in meta.urls:
            if retry and meta.url(url).youtube == 'failed':
                logger.debug('Retrying previously failed url {0}'.format(url))
            else:
                continue

        process_url(meta, url, None, dry_run, email, passwd, keep=keep)

def download_archive(page_url, directory, zip_url=None):
    logger = logging.getLogger('dl')

    def url_file_name(fh):
        try:
            _, params = cgi.parse_header(fh.headers['content-disposition'])
            return params['filename']
        except KeyError:
            pass # header not found, fall back on parsing url

        url = urlparse.urlparse(fh.geturl())
        path = urllib.unquote_plus(url.path)
        fname = path.rsplit('/', 1)[-1]
        logger.debug(u'Content-disposition missing, fallback file name {0}'.format(fname))
        return fname

    opener = urllib2.build_opener()
    opener.addheaders = [('user-agent', USER_AGENT)]

    if not zip_url:
        html = opener.open(page_url).read()
        # fragile ...
        m = re.search(r'\<a href="([^"]+)"\>MP3 Download', html)
        assert m != None
        zip_url = m.group(1)
        logger.debug(u'Found archive url: {0}'.format(zip_url))

    with contextlib.closing(opener.open(zip_url)) as inf:
        chunk_size = 8192
        total_size = int(inf.headers['content-length'])
        read = 0
        nsteps = 10
        step = int(total_size / nsteps)

        archive = os.path.join(directory, url_file_name(inf))

        with open(archive, 'w') as outf:
            logger.info(u'Download size {0}M, destination {1}'.format(total_size/1024/1024, archive))

            while True:
                chunk = inf.read(chunk_size)
                if not chunk:
                    break
                outf.write(chunk)

                read += len(chunk)
                if read / step > (read-len(chunk)) / step:
                    logger.debug(u'{0} %'.format(int(100.0*read/step/nsteps)))

    logger.debug('Download complete')
    return archive

def process_url(meta, page_url, zip_url=None, dry_run=False, email=None, passwd=None, keep=False):
    logger = logging.getLogger('url')
    logger.info(u'Processing {0}'.format(page_url))

    (email, passwd) = ask_email_password(email, passwd)

    try:
        with TemporaryDir('ektobot', keep=keep) as dname:
            archive = download_archive(page_url, dname, zip_url)
            mp3_dir = unpack(archive, dry_run=False, outdir=dname)
            video_dir = os.path.join(dname, 'video')
            videos(mp3_dir, dry_run=False, outdir=video_dir, cover=None)
            ytupload(video_dir, dry_run=dry_run, email=email, passwd=passwd, url=page_url)
    except KeyboardInterrupt:
        raise
    except:
        logger.exception(u'Album processing failed')
        result = 'failed'
    else:
        logger.info(u'Album successfully uploaded')
        result = 'done-unknown-id'

    meta.url(page_url).youtube = result
    meta.save(dry_run=dry_run)
