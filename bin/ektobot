#!/usr/bin/python

import re
import sys
import logging
import argparse

from ektobot.youtube import ytupload
from ektobot.utils import ask_email_password, read_meta, write_meta
from ektobot.unpack import unpack
from ektobot.video_convert import videos
from ektobot.network import new_rss, watch_rss, process_url, process_list

#def parse_format(string, fmt, variables):
#    # create RE
#    fmt = re.escape(fmt)
#    for var in variables:
#        fmt = fmt.replace('\{'+var+'\}', '(?P<'+var+'>.*)')
#
#    # run RE on string
#    m = re.match(fmt, string)
#    if m:
#        return m.groupdict()
#
#    raise ValueError('String did not match input format')
#
#def transform_format(string, informat, outformat, variables):
#    parsed = parse_format(string, informat, variables)
#    return outformat.format(**parsed)
#
#def reorder_video_description(yt_service, video_id):
#    entry = yt_service.GetYouTubeVideoEntry(video_id=video_id)
#    entry.media.description.text = transform_format(
#            entry.media.description.text,
#            old_ektoplazm_description,
#            ektoplazm_description,
#            ['artist', 'track', 'album', 'trackno', 'albumurl'])
#    yt_service.debug = True                  # problem somewhere here
#    print yt_service.UpdateVideoEntry(entry) #

def setup_logging(filename=None):
    fmt = logging.Formatter(
            fmt='%(asctime)s %(name)-8s %(levelname)-7s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    root = logging.getLogger('')
    root.setLevel(logging.DEBUG)

    log_stderr = logging.StreamHandler(sys.stderr)
    log_stderr.setFormatter(fmt)
    log_stderr.setLevel(logging.INFO)
    root.addHandler(log_stderr)

    if filename:
        log_file = logging.FileHandler(filename=filename)
        log_file.setFormatter(fmt)
        log_file.setLevel(logging.DEBUG)
        root.addHandler(log_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument('-n', '--dry-run', action='store_true', help='do not write/upload anything')
    parser.add_argument('-l', '--login', type=str, help='youtube login (email)')
    parser.add_argument('-p', '--password', type=str, help='youtube password')
    parser.add_argument('-k', '--keep-tempfiles', action='store_true', help='do not delete the downloaded and generated files')
    parser.add_argument('-L', '--log-file', type=str, help='log file path')
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

    parser_rss_new = subparsers.add_parser('rss-new', help='create metadata for rss feed')
    parser_rss_new.add_argument('-o', '--output', type=str, help='metadata file name')
    parser_rss_new.add_argument('url', type=str, help='url of the feed')
    parser_rss_new.set_defaults(what='rss-new')

    parser_rss = subparsers.add_parser('rss', help='watch rss feed')
    parser_rss.add_argument('meta', type=str, help='metadata file (create w/ rss-new)')
    parser_rss.set_defaults(what='rss')

    parser_url = subparsers.add_parser('url', help='process ektoplazm url - download album, convert to videos and upload to youtube')
    parser_url.add_argument('url', type=str, help='ektoplazm album url')
    parser_url.add_argument('-m', '--meta', type=str, help='json file with metadata')
    parser_url.set_defaults(what='url')

    parser_list = subparsers.add_parser('list', help='process list of urls read from a file')
    parser_list.add_argument('meta', type=str, help='metadata file (same as for rss)')
    parser_list.add_argument('urls', type=str, help='json file with the url list')
    parser_list.add_argument('-f', '--retry-failing', action='store_true', help='retry urls marked as failed')
    parser_list.set_defaults(what='list')

    args = parser.parse_args()
    setup_logging(args.log_file)
    logging.info('ektobot started')

    try:
        if args.what == 'unpack':
            unpack(args.archive, args.dry_run)
        elif args.what == 'videos':
            videos(args.dir, args.dry_run, args.outdir, args.image)
        elif args.what == 'youtube':
            ytupload(args.dir, args.dry_run, args.login, args.password, args.url)
        elif args.what == 'rss-new':
            new_rss(args.url, args.output)
        elif args.what == 'rss':
            watch_rss(args.meta, args.dry_run, email=args.login, passwd=args.password, keep=args.keep_tempfiles) #tmpdir, sleep interval
        elif args.what == 'url':
            process_url(args.url, zip_url=None, dry_run=args.dry_run, email=args.login, passwd=args.password, keep=args.keep_tempfiles, metafile=args.meta)
        elif args.what == 'list':
            process_list(args.meta, args.urls, dry_run=args.dry_run, email=args.login, passwd=args.password, keep=args.keep_tempfiles, retry=args.retry_failing)
        else:
            assert False
    except KeyboardInterrupt:
        pass
    except:
        logging.exception('Uncaught exception')

    logging.info('ektobot terminating')
