#!/usr/bin/python

import os
import re
import cgi
import json
import time
import shutil
import os.path
import urllib2
import zipfile
import argparse
import tempfile
import traceback
import contextlib
import subprocess

@contextlib.contextmanager
def TemporaryDir(name='tmp', keep=False):
    dname = tempfile.mkdtemp(prefix=name+'.')
    try:
        yield dname
    finally:
        if not keep:
            shutil.rmtree(dname)

def parse_name(filename):
    (dn, fn) = os.path.split(filename)
    m = re.match(r'^(.+) - (.+) - (\d+) - MP3\.zip$', fn)
    return {
        'artist': m.group(1),
        'album' : m.group(2),
        'year'  : m.group(3)
    }

def dir_name(album):
    return album['artist'].replace(' ', '_') + '_-_' + album['album'].replace(' ', '_') + '/'

def trackmeta(f):
    import eyeD3

    tag = eyeD3.tag.Mp3AudioFile(f).getTag()
    return {
        'num'   : tag.getTrackNum()[0],
        'artist': tag.getArtist(),
        'track' : tag.getTitle(),
        'bpm'   : tag.getBPM(),
        'year'  : tag.getYear(),
        'album' : tag.getAlbum()
    }

def run(args):
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(u'Subprocess failed w/ return code {0}, stderr:\n {1}'.format(p.returncode, err))

def write_meta(dirname, meta, dry_run=False, filename='ektobot.json'):
    if dry_run:
        return

    with open(os.path.join(dirname, filename), 'w') as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)

def read_meta(dirname, filename='ektobot.json'):
    with open(os.path.join(dirname, filename), 'r') as fh:
        meta = json.load(fh)
    return meta

def unpack(archive, dry_run, outdir='.'):
    #TODO write to temporary directory first (album artist fallback to dir name)
    #metadata: album artist + album name
    album = parse_name(archive)
    dirname = os.path.join(outdir, dir_name(album))
    if not dry_run:
        os.mkdir(dirname)

    with zipfile.ZipFile(archive, 'r') as zipf:
        print u'Extracting {0} to {1} ...'.format(archive, dirname)
        if not dry_run:
            zipf.extractall(dirname)

    #fix archives with extra directory level
    (_, dirs, files) = next(os.walk(dirname))
    if len(dirs) == 1 and len(files) == 0:
        print 'Extra directory level detected, removing ...'
        nested_dir = os.path.join(dirname, dirs[0])
        (_, dirs, files) = next(os.walk(nested_dir))
        for f in dirs + files:
            src = os.path.join(nested_dir, f)
            shutil.move(src, dirname)
        shutil.rmtree(nested_dir)

    write_meta(dirname, album, dry_run)

    return dirname

def find_cover(dirname):
    (_, __, files) = next(os.walk(dirname))

    f_suffix = lambda f: (f.lower().endswith('.jpg') or f.lower().endswith('.png'))
    files = filter(f_suffix, files)

    patterns = [
        r'^folder\.jpg$',
        r'^cover\....$',
        r'front\....$',
        r'image 1',
        r'cover',
        r'front',
    ]
    for p in patterns:
        for f in files:
            if re.search(p, f, flags=re.IGNORECASE):
                return os.path.join(dirname, f)

    files.sort()
    if files:
        return os.path.join(dirname, files[0])

    return None

def videos(dirname, dry_run, outdir=None, cover=None):
    if not outdir:
        outdir = os.path.join(dirname, 'video')
    if not os.path.isdir(outdir):
        print u'Creating output directory {0}'.format(outdir)
        os.mkdir(outdir)

    if not cover:
        cover = find_cover(dirname)
    if not cover or not os.path.exists(cover):
        raise RuntimeError(u'Cover {0} not found'.format(cover))
    print u'Using image {0} as a cover'.format(cover)

    try:
        meta = read_meta(dirname)
        meta['tracks'] = []
    except IOError:
        # if there's no .json, read the album metadata from the first track
        meta = None

    (_, _, files) = next(os.walk(dirname))
    for infile in sorted(files):
        if not infile.endswith('.mp3'):
            continue

        tmeta = trackmeta(os.path.join(dirname, infile))
        if not meta:
            meta = {
                'artist': tmeta['artist'],
                'album' : tmeta['album'],
                'year'  : tmeta['year'],
                'tracks': []
            }
        # no need to write it to disk
        del tmeta['album']

        outfile = os.path.join(outdir, infile.decode('utf-8', 'replace').encode('ascii', 'replace'))
        outfile = outfile[:-3] + 'avi'
        meta['tracks'].append(tmeta)
        meta['tracks'][-1]['video_file'] = os.path.basename(outfile)
        infile = os.path.join(dirname, infile)

        print u'Converting {0} '.format(infile)
        print u'        to {0} ...'.format(outfile)
        cmdline = ['ffmpeg',
                   '-loglevel', 'error', # be quiet
                   '-n',                 # do not overwrite output files
                   '-loop', '1',         # video = image
                   '-i', cover,          # image
                   '-i', infile,         # audio
                   '-vf', 'scale=min(800\,in_w):-1', # scale the image down to (at most) 800px width
                   '-r', '1',            # 1fps
                   '-acodec', 'copy',    # do not recode audio
                   '-shortest',          # stop when the audio stops
                   outfile]
        try:
            if not dry_run:
                run(cmdline)
            else:
                print ' '.join(cmdline)
        except:
            print u'Converting {0} failed'.format(infile)
            raise

    write_meta(outdir, meta, False)
    print 'Done!'

ektoplazm_description = u'''Artist: {artist}
Track: {track}
Album: {album}
Track number: {trackno}

Download the full album from Ektoplazm: {albumurl}'''

default_description = u'''Artist: {artist}
Track: {track}
Album: {album}
Track number: {trackno}

Uploaded by ektobot http://github.com/mmilata/ektobot'''

templates = {
    'default'  : default_description,
    'ektoplazm': ektoplazm_description
}

def ask_email_password(email=None, passwd=None):
    import getpass
    if not email:
        email = raw_input('youtube login: ') #XXX ektobot42@gmail.com

    if not passwd:
        passwd = getpass.getpass('password: ')

    return (email, passwd)

def ytupload(dirname, dry_run, email, passwd, url=None):
    import gdata.youtube
    import gdata.youtube.service

    def yt_upload_video(yt_service, filename, title, description):
        media_group = gdata.media.Group(
            title       = gdata.media.Title(text=title),
            description = gdata.media.Description(description_type='plain', text=description),
            keywords    = gdata.media.Keywords(text='ektoplazm, music'),
            category    = gdata.media.Category(text='Music', label='Music', scheme='http://gdata.youtube.com/schemas/2007/categories.cat'),
            player      = None
        )

        video_entry = gdata.youtube.YouTubeVideoEntry(media=media_group)
        new_entry = yt_service.InsertVideoEntry(video_entry, filename)
        return new_entry.id.text.split('/')[-1]

    def yt_create_playlist(yt_service, title, description, ids):
        playlist = yt_service.AddPlaylist(title, description)
        playlist_uri = playlist.feed_link[0].href #magic...
        for video_id in ids:
            playlist_entry = yt_service.AddPlaylistVideoEntryToPlaylist(playlist_uri, video_id)

    meta = read_meta(dirname)
    playlist_ids = []

    desc_template = templates['default']
    if url and 'ektoplazm.com' in url:
        desc_template = templates['ektoplazm']

    (email, passwd) = ask_email_password(email, passwd)

    yt_service = gdata.youtube.service.YouTubeService()
    #yt_service.ssl = True
    yt_service.developer_key = 'AI39si5d9grkxFwwm603wvh2toZxshBqVkCWalTT3UXB4b3W3TJz0bCwBv0qqRN9LeQDz0FAXOfCaSW35mAbtj3pnI8cXKu7YA'
    yt_service.source = 'ektobot'
    yt_service.client_id = 'ektobot-0'
    yt_service.email = email
    yt_service.password = passwd
    yt_service.ProgrammaticLogin()

    for trk in meta['tracks']:
        filename = os.path.join(dirname, trk['video_file'])
        title = u'{0} - {1}'.format(trk['artist'], trk['track'])
        description = desc_template.format(
            artist = trk['artist'],
            track = trk['track'],
            album = meta['album'],
            trackno = trk['num'],
            albumurl = url if url else 'http://www.example.org/' #'http://www.ektoplazm.com/'
        )
        print u'Uploading {0} as {1} with description:\n{2}\n'.format(filename, title, description)
        if not dry_run:
            vid_id = yt_upload_video(yt_service, filename, title, description)
            playlist_ids.append(vid_id)
        print 'Upload complete'
        time.sleep(60) # youtube's not happy when we're uploading too fast

    if meta['artist'] == 'VA':
        pls_name = u'{0} ({1})'.format(meta['album'], meta['year'])
    else:
        pls_name = u'{0} - {1} ({2})'.format(meta['artist'], meta['album'], meta['year'])
    pls_description = ''
    print u'Creating playlist {0}'.format(pls_name)
    if not dry_run:
        yt_create_playlist(yt_service, pls_name, pls_description, playlist_ids)
    print 'Playlist created'

def new_rss(url, outfile='ektobot.json'):
    meta = {
        'url': url,
        'albums': {}
    }

    write_meta('.', meta, False) #XXX use outfile arg

def watch_rss(metafile, dry_run, email=None, passwd=None, keep=False, sleep_interval=15*60):
    import feedparser

    def mp3_link(e):
        for l in e.links:
            if 'rel' in l and l.rel == 'enclosure' and 'title' in l and l.title == 'MP3 Download':
                return l.href
        return None

    meta = read_meta('.') # XXX use metafile arg
    (email, passwd) = ask_email_password(email, passwd)

    while True:
        feed = feedparser.parse(meta['url']) # XXX may throw exception

        for entry in feed.entries:
            if entry.link not in meta['albums']:
                try:
                    process_url(entry.link, mp3_link(entry), dry_run, email, passwd, keep=keep)
                    meta['albums'][entry.link] = 'OK'
                except KeyboardInterrupt:
                    raise
                except:
                    print traceback.format_exc()
                    print 'Album processing failed'
                    meta['albums'][entry.link] = 'FAIL'
                write_meta('.', meta)
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print 'User requested exit'
            break

def process_list(metafile, listfile, dry_run, email=None, passwd=None, keep=False):

    meta = read_meta('.') # use metafile arg
    assert meta.has_key('albums')

    urls = read_meta('.', filename=listfile)
    (email, passwd) = ask_email_password(email, passwd)

    for url in urls:
        if url in meta['albums']:
            continue

        try:
            process_url(url, None, dry_run, email, passwd, keep=keep)
            meta['albums'][url] = 'OK'
        except KeyboardInterrupt:
            raise
        except:
            print traceback.format_exc()
            print 'Album processing failed'
            meta['albums'][url] = 'FAIL'
        write_meta('.', meta)

def process_url(page_url, zip_url=None, dry_run=False, email=None, passwd=None, keep=False):

    if not zip_url:
        html = urllib2.urlopen(page_url).read()
        # fragile ...
        m = re.search(r'\<a href="([^"]+)"\>MP3 Download', html)
        assert m != None
        zip_url = m.group(1)

    (email, passwd) = ask_email_password(email, passwd)

    print u'Processing {0}'.format(page_url)

    with TemporaryDir('ektobot', keep=keep) as dname, \
            contextlib.closing(urllib2.urlopen(zip_url)) as inf:
        chunk_size = 8192
        total_size = int(inf.headers['content-length'])
        read = 0
        nsteps = 10
        step = int(total_size / nsteps)

        _, params = cgi.parse_header(inf.headers['content-disposition'])
        archive = os.path.join(dname, params['filename'])

        with open(archive, 'w') as outf:
            print u'Download size {0}M, destination {1}'.format(total_size/1024/1024, archive)

            while True:
                chunk = inf.read(chunk_size)
                if not chunk:
                    break
                outf.write(chunk)

                read += len(chunk)
                if read / step > (read-len(chunk)) / step:
                    print u'{0} %'.format(int(100.0*read/step/nsteps))

            print 'Download complete'

        mp3_dir = unpack(archive, dry_run=False, outdir=dname)
        video_dir = os.path.join(dname, 'video')
        videos(mp3_dir, dry_run=False, outdir=video_dir, cover=None)
        ytupload(video_dir, dry_run=dry_run, email=email, passwd=passwd, url=page_url)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument('-n', '--dry-run', action='store_true', help='do not write/upload anything')
    parser.add_argument('-l', '--login', type=str, help='youtube login (email)')
    parser.add_argument('-p', '--password', type=str, help='youtube password')
    parser.add_argument('-k', '--keep-tempfiles', action='store_true', help='do not delete the downloaded and generated files')
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
    parser_url.set_defaults(what='url')

    parser_list = subparsers.add_parser('list', help='process list of urls read from a file')
    parser_list.add_argument('meta', type=str, help='metadata file (same as for rss)')
    parser_list.add_argument('urls', type=str, help='json file with the url list')
    parser_list.set_defaults(what='list')

    args = parser.parse_args()
    #print args
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
        process_url(args.url, zip_url=None, dry_run=args.dry_run, email=args.login, passwd=args.password, keep=args.keep_tempfiles) # metadata file
    elif args.what == 'list':
        process_list(args.meta, args.urls, dry_run=args.dry_run, email=args.login, passwd=args.password, keep=args.keep_tempfiles)
    else:
        assert False
