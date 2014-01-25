
import os
import re
import logging
import os.path

from utils import read_dirmeta, write_dirmeta, run

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

def clean_string(s):
    return s.decode('utf-8', 'replace').encode('ascii', 'replace')

def trackmeta(f):

    try:
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

    except ImportError:
        import eyed3
        tag = eyed3.load(f).tag

        return {
            'num'   : tag.track_num,
            'artist': tag.artist,
            'track' : tag.title,
            'bpm'   : tag.bpm,
            'year'  : tag.best_release_date.year,
            'album' : tag.album
        }

def videos(dirname, dry_run, outdir=None, cover=None):
    logger = logging.getLogger('video')

    if not outdir:
        outdir = os.path.join(dirname, 'video')
    if not os.path.isdir(outdir):
        logger.debug(u'Creating output directory {0}'.format(outdir))
        os.mkdir(outdir)

    if not cover:
        cover = find_cover(dirname)
    if not cover or not os.path.exists(cover):
        raise RuntimeError(u'Cover {0} not found'.format(cover))
    logger.info(u'Using image {0} as a cover'.format(cover))

    try:
        meta = read_dirmeta(dirname)
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

        outfile = os.path.join(outdir, clean_string(infile))
        outfile = outfile[:-3] + 'avi'
        meta['tracks'].append(tmeta)
        meta['tracks'][-1]['video_file'] = os.path.basename(outfile)
        infile = os.path.join(dirname, infile)

        logger.info(u'Converting {0}'.format(os.path.basename(clean_string(infile))))
        cmdline = ['ffmpeg',
                   '-loglevel', 'error', # be quiet
                   '-n',                 # do not overwrite output files
                   '-loop', '1',         # video = image
                   '-i', cover,          # image
                   '-i', infile,         # audio
                   '-vf', 'scale=min(800\\,in_w):-1', # scale the image down to (at most) 800px width
                   '-r', '1',            # 1fps
                   '-acodec', 'copy',    # do not recode audio
                   '-shortest',          # stop when the audio stops
                   outfile]
        try:
            if not dry_run:
                run(cmdline)
            else:
                logger.debug(' '.join(cmdline))
        except:
            logger.error(u'Converting {0} failed'.format(clean_string(infile)))
            raise

    write_dirmeta(outdir, meta, dry_run=False)
    logger.info('Done!')
