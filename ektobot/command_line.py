
import sys
import os.path
import logging
import argparse

from state import State
from youtube import ytupload
from utils import load_config, AuthData
from unpack import unpack
from video_convert import videos
from network import watch_rss, process_url, process_list

def setup_logging(filename=None, verbose=False):
    fmt = logging.Formatter(
            fmt='%(asctime)s %(levelname)-7s %(name)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    root = logging.getLogger('')
    root.setLevel(logging.DEBUG)

    log_stderr = logging.StreamHandler(sys.stderr)
    log_stderr.setFormatter(fmt)
    log_stderr.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.addHandler(log_stderr)

    if filename:
        log_file = logging.FileHandler(filename=filename)
        log_file.setFormatter(fmt)
        log_file.setLevel(logging.DEBUG)
        root.addHandler(log_file)

def tobool(s):
    if s.lower() in ('yes', 'true', 'on', '1'):
        return True
    elif s.lower() in ('no', 'false', 'off', '0'):
        return False
    else:
        raise ValueError('Invalid boolean value in configuration')

def set_defaults_from_config(cfgfile, parser):
    if cfgfile:
        cfg = load_config(cfgfile)
    else:
        # try the default, don't fail if it doesn't exist
        try:
            cfg = load_config(os.path.expanduser('~/.ektobot/config'))
        except IOError:
            return

    config_subs = {
        'log_file':       ('main', 'log_file', os.path.expanduser),
        'state_file':     ('main', 'state_file', os.path.expanduser),
        'keep_tempfiles': ('main', 'keep_tempfiles', tobool),
        'yt_login':    ('youtube', 'login', None),
        'yt_password': ('youtube', 'password', None),
        'reddit_login':    ('reddit', 'login', None),
        'reddit_password': ('reddit', 'password', None),
        'reddit_sub':      ('reddit', 'sub', None),
    }

    for opt_name, (section, key, f) in config_subs.iteritems():
        try:
            v = cfg[section][key]
        except KeyError:
            continue
        if f:
            v = f(v)
        parser.set_defaults(**{opt_name: v})

def process_command_line(args):
    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument('-c', '--config', type=str, help='configuration file')
    parser.add_argument('-m', '--state-file', type=str, help='state file (meta)')
    parser.add_argument('-n', '--dry-run', action='store_true', help='do not write/upload anything')
    parser.add_argument('-k', '--keep-tempfiles', action='store_true', help='do not delete the downloaded and generated files')
    parser.add_argument('-L', '--log-file', type=str, help='log file path')
    parser.add_argument('--yt-login', type=str, help='youtube login (email)')
    parser.add_argument('--yt-password', type=str, help='youtube password')
    parser.add_argument('--reddit-login', type=str, help='reddit login')
    parser.add_argument('--reddit-password', type=str, help='reddit password')
    parser.add_argument('--reddit-sub', type=str, help='subreddit')
    parser.add_argument('-i', '--interactive', action='store_true', help='stop to ask questions')
    parser.add_argument('-v', '--verbose', action='store_true', help='debugging output')
    subparsers = parser.add_subparsers(help='description', metavar='COMMAND', title='commands')

    parser_unpack = subparsers.add_parser('unpack', help='unpack .zip archive')
    parser_unpack.add_argument('archive', type=str, help='input file')
    parser_unpack.set_defaults(what='unpack')

    parser_videos = subparsers.add_parser('videos', help='convert audio files to yt-uploadable videos')
    parser_videos.add_argument('--image', type=str, help='album cover image')
    parser_videos.add_argument('--outdir', type=str, help='video output directory (default video)')
    parser_videos.add_argument('dir', type=str, help='directory containing audio files') #TODO make it optional?
    parser_videos.set_defaults(what='videos')

    parser_yt = subparsers.add_parser('youtube', help='upload videos to youtube.com')
    parser_yt.add_argument('dir', type=str, help='directory containing the videos')
    parser_yt.add_argument('-u', '--url', type=str, help='ektoplazm url of the album')
    parser_yt.set_defaults(what='youtube')

    parser_reddit = subparsers.add_parser('reddit', help='post link to video to reddit')
    parser_reddit.add_argument('url', type=str, help='ektoplazm url (needs to be already uploaded to youtube)')
    parser_reddit.set_defaults(what='reddit')

    parser_rss_new = subparsers.add_parser('set-url', help='create metadata for rss feed')
    parser_rss_new.add_argument('url', type=str, help='url of the feed')
    parser_rss_new.set_defaults(what='set-url')

    parser_rss = subparsers.add_parser('rss', help='watch rss feed')
    parser_rss.set_defaults(what='rss')

    parser_url = subparsers.add_parser('url', help='process ektoplazm url - download album, convert to videos and upload to youtube')
    parser_url.add_argument('url', type=str, help='ektoplazm album url')
    parser_url.set_defaults(what='url')

    parser_list = subparsers.add_parser('list', help='process list of urls read from a file')
    parser_list.add_argument('urls', type=str, help='json file with the url list')
    parser_list.add_argument('-f', '--retry-failing', action='store_true', help='retry urls marked as failed')
    parser_list.set_defaults(what='list')

    # don't bother, just parse it twice
    opts = parser.parse_args(args)
    set_defaults_from_config(opts.config, parser)
    return parser.parse_args(args)


def main(args):
    opts = process_command_line(args)
    setup_logging(opts.log_file, opts.verbose)
    logging.info('ektobot started')

    exitcode = 0

    try:
        auth = AuthData(
            yt_login=opts.yt_login,
            yt_password=opts.yt_password,
            reddit_login=opts.reddit_login,
            reddit_password=opts.reddit_password,
        )
        if opts.what in ('set-url', 'rss', 'url', 'list', 'reddit'):
            meta = State(opts.state_file)

        if opts.what == 'unpack':
            unpack(opts.archive, opts.dry_run)
        elif opts.what == 'videos':
            videos(opts.dir, opts.dry_run, opts.outdir, opts.image)
        elif opts.what == 'youtube':
            ytupload(opts.dir, opts.dry_run, auth, opts.url)
        elif opts.what == 'reddit':
            submit_to_reddit(meta.url(opts.url, create=False), opts.reddit_sub, auth,
                             interactive=opts.interactive, dry_run=opts.dry_run)
            meta.save(dry_run=opts.dry_run)
        elif opts.what == 'set-url':
            meta.feed = opts.url
            meta.save(dry_run=opts.dry_run)
        elif opts.what == 'rss':
            watch_rss(meta, opts.dry_run, auth=auth, keep=opts.keep_tempfiles,
                      subreddit=opts.reddit_sub, interactive=opts.interactive)
        elif opts.what == 'url':
            process_url(meta, opts.url, dry_run=opts.dry_run, auth=auth, keep=opts.keep_tempfiles,
                        subreddit=opts.reddit_sub, interactive=opts.interactive)
        elif opts.what == 'list':
            process_list(opts.state_file, opts.urls, dry_run=opts.dry_run, auth=auth,
                         keep=opts.keep_tempfiles, retry=opts.retry_failing)
        else:
            assert False
    except KeyboardInterrupt:
        pass
    except:
        logging.exception('Uncaught exception')
        exitcode = 1

    logging.info('ektobot terminating')
    sys.exit(exitcode)
