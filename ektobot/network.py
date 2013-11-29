
import json
import time
import os.path
import logging

from unpack import unpack
from utils import TemporaryDir
from video_convert import videos
from youtube import ytupload
from source import Ektoplazm

def watch_rss(meta, dry_run, auth=None, keep=False, sleep_interval=30*60):
    import feedparser

    logger = logging.getLogger('rss')

    def mp3_link(e):
        for l in e.links:
            if 'rel' in l and l.rel == 'enclosure' and 'title' in l and l.title == 'MP3 Download':
                return l.href
        return None

    while True:
        feed = feedparser.parse(meta.feed) # XXX may throw exception

        for entry in feed.entries:
            if entry.link not in meta.urls:
                process_url(meta, entry.link, mp3_link(entry), dry_run, auth=auth,
                            keep=keep)
        try:
            time.sleep(sleep_interval)
        except KeyboardInterrupt:
            logger.info('User requested exit')
            break

def process_list(meta, listfile, dry_run, auth=None, keep=False, retry=False):
    logger = logging.getLogger('list')

    with open(listfile, 'r') as fh:
        urls = json.load(fh)

    for url in urls:
        if url in meta.urls:
            if retry and meta.url(url).youtube == 'failed':
                logger.debug('Retrying previously failed url {0}'.format(url))
            else:
                continue

        process_url(meta, url, None, dry_run, auth=auth, keep=keep)

def download_archive(page_url, directory, zip_url=None):
    e = Ektoplazm(page_url)
    return e.download_archive(directory)

def process_url(meta, page_url, zip_url=None, dry_run=False, auth=None, keep=False):
    logger = logging.getLogger('url')
    logger.info(u'Processing {0}'.format(page_url))

    try:
        with TemporaryDir('ektobot', keep=keep) as dname:
            archive = download_archive(page_url, dname)
            mp3_dir = unpack(archive, dry_run=False, outdir=dname)
            video_dir = os.path.join(dname, 'video')
            videos(mp3_dir, dry_run=False, outdir=video_dir, cover=None)
            ytupload(video_dir, dry_run=dry_run, auth=auth, url=page_url)
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
