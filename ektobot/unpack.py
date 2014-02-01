
import os
import re
import shutil
import logging
import os.path
import zipfile

from utils import write_dirmeta

# TODO: source-specific
# XXX and unreliable if artist/album contain dash - better get it from id3
def parse_name(filename):
    fn = os.path.basename(filename)
    m = re.match(r'^(.+) - (.+) - (\d+) - MP3\.zip$', fn)
    return {
        'artist': m.group(1),
        'album' : m.group(2),
        'year'  : m.group(3)
    }

def dir_name(album):
    return album['artist'].replace(' ', '_') + '_-_' + album['album'].replace(' ', '_') + '/'

# TODO: source-specific
def unpack(archive, dry_run, outdir='.', urlmeta=None):
    logger = logging.getLogger('unpack')
    #TODO write to temporary directory first (album artist fallback to dir name)
    #metadata: album artist + album name
    album = parse_name(archive)
    dirname = os.path.join(outdir, dir_name(album))
    if not dry_run:
        os.mkdir(dirname)

    with zipfile.ZipFile(archive, 'r') as zipf:
        logger.info(u'Extracting {0} to {1} ...'.format(archive, dirname))
        if not dry_run:
            zipf.extractall(dirname)

    #fix archives with extra directory level
    (_, dirs, files) = next(os.walk(dirname))
    if len(dirs) == 1 and len(files) == 0:
        logger.info('Extra directory level detected, removing ...')
        nested_dir = os.path.join(dirname, dirs[0])
        (_, dirs, files) = next(os.walk(nested_dir))
        for f in dirs + files:
            src = os.path.join(nested_dir, f)
            shutil.move(src, dirname)
        shutil.rmtree(nested_dir)

    if urlmeta:
        album['url'] = urlmeta.url
        album['license'] = urlmeta.license
        album['tags'] = list(urlmeta.tags)
        urlmeta.artist = album['artist']
        urlmeta.title = album['album']
        urlmeta.year = int(album['year'])

    write_dirmeta(dirname, album, dry_run)

    return dirname

