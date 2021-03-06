
import json
import time
import os.path
import logging

from unpack import unpack
from utils import TemporaryDir
from video_convert import videos
from youtube import ytupload
from source import Ektoplazm
from reddit import submit_to_reddit

#XXX the number of arguments is not ... sustainable
def watch_rss(meta, dry_run, auth=None, keep=False, sleep_interval=30*60,
              subreddit=None, interactive=None):
    import feedparser

    logger = logging.getLogger('rss')

    while True:
        feed = feedparser.parse(meta.feed) # XXX may throw exception

        for entry in feed.entries:
            if not meta.is_processed(entry.link):
                process_url(meta, entry.link, dry_run, auth=auth, keep=keep,
                            subreddit=subreddit, interactive=interactive)
        try:
            time.sleep(sleep_interval)
        except KeyboardInterrupt:
            logger.info('User requested exit')
            break

def process_list(meta, listfile, dry_run, auth=None, keep=False, retry=False,
                 subreddit=None, interactive=None):
    logger = logging.getLogger('list')

    with open(listfile, 'r') as fh:
        urls = json.load(fh)

    for url in urls:
        if meta.is_processed(url):
            if retry and meta.url(url).youtube == 'failed':
                logger.debug('Retrying previously failed url {0}'.format(url))
            else:
                continue

        process_url(meta, url, dry_run, auth=auth, keep=keep,
                    subreddit=subreddit, interactive=interactive)

def process_url(meta, page_url, dry_run=False, auth=None, keep=False,
                subreddit=None, interactive=False):
    logger = logging.getLogger('url')
    logger.info(u'Processing {0}'.format(page_url))

    urlmeta = meta.url(page_url)
    try:
        with TemporaryDir('ektobot', keep=keep) as dname:
            e = Ektoplazm(page_url)
            logger.info(u'tags: ' + u', '.join(e.tags))
            archive = e.download_archive(dname)
            urlmeta.tags = e.tags
            urlmeta.license = e.license.url
            mp3_dir = unpack(archive, dry_run=False, outdir=dname, urlmeta=urlmeta)
            video_dir = os.path.join(dname, 'video')
            videos(mp3_dir, dry_run=False, outdir=video_dir, cover=None)
            (playlist_id, video_ids) = ytupload(video_dir, dry_run=dry_run, secrets_file=auth.yt_secrets)
    except KeyboardInterrupt:
        raise
    except:
        logger.exception(u'Album processing failed')
        urlmeta.youtube.result = 'failed'
    else:
        logger.info(u'Album successfully uploaded')
        urlmeta.youtube.result = 'done'
        urlmeta.youtube.playlist = playlist_id
        urlmeta.youtube.videos = video_ids
    meta.save(dry_run=dry_run)

    if subreddit and urlmeta.youtube.result == 'done':
        try:
            urlmeta.reddit.result = None
            submit_to_reddit(urlmeta, subreddit, auth, interactive=interactive, dry_run=dry_run)
        except Exception:
            logger.exception(u'Failed to submit to reddit')
            if not urlmeta.reddit.result:
                urlmeta.reddit.result = 'failed'
            # TODO: save the exception
        meta.save(dry_run=dry_run)
