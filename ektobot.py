#!/usr/bin/python

import os
import re
import json
import os.path
import zipfile
import argparse
import subprocess

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

def trackmeta(filelist):
    res = []
    for f in sorted(filelist):
        m = re.match(r'^(\d+) - (.+) - (.+)\.mp3$', f)
        if not m:
            continue
        res.append({
            'num'   : int(m.group(1)),
            'artist': m.group(2),
            'track' : m.group(3),
            'audio' : f
        })

    return res

def run(args):
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    if p.returncode != 0:
        raise RuntimeError('Subprocess failed w/ return code {0}, stderr:\n {1}')

def write_meta(dirname, meta, dry_run=False):
    if dry_run:
        return

    with open(os.path.join(dirname, 'ektobot.json'), 'w') as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)

def unpack(archive, dry_run):
    album = parse_name(archive)
    dirname = dir_name(album)
    if not dry_run:
        os.mkdir(dirname)

    with zipfile.ZipFile(archive, 'r') as zipf:
        print 'Extracting {0} to {1} ...'.format(archive, dirname)
        if not dry_run:
            zipf.extractall(dirname)
        names = zipf.namelist()

    album['tracks'] = trackmeta(names)
    write_meta(dirname, album, dry_run)

    return dirname

def videos(dirname, dry_run):
    outdir = os.path.join(dirname, 'video')
    if not os.path.isdir(outdir):
        print 'Creating output directory {0}'
        os.mkdir(outdir)

    with open(os.path.join(dirname, 'ektobot.json'), 'r') as fh:
        meta = json.load(fh)

    cover = os.path.join(dirname, 'folder.jpg')
    if not os.path.exists(cover):
        raise RuntimeError('Cover {0} not found'.format(cover))
    print 'Using image {0} as a cover'.format(cover)

    for (idx, trk) in enumerate(meta['tracks']):
        infile = trk['audio']
        outfile = os.path.join(outdir, infile)
        outfile = outfile[:-3] + 'avi'
        infile = os.path.join(dirname, infile)
        print 'Converting {0} '.format(infile)
        print '        to {0} ...'.format(outfile)
        cmdline = ['ffmpeg',
                   '-loglevel', 'error', # be quiet
                   '-n',                 # do not overwrite output files
                   '-loop_input',        # video = image
                   '-i', cover,          # image
                   '-i', infile,         # audio
                   '-r', '1',            # 1fps
                   '-acodec', 'copy',    # do not recode audio
                   '-shortest',          # stop when the audio stops
                   outfile]
        try:
            if not dry_run:
                run(cmdline)
            else:
                print ' '.join(cmdline)
            meta['tracks'][idx]['video'] = os.path.basename(outfile)
        except:
            print 'Converting {0} failed'.format(infile)
            raise

    meta['videodir'] = 'video'
    write_meta(dirname, meta, False)
    print 'Done!'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument('-n', '--dry-run', action='store_true', help='only print what will be done')
    subparsers = parser.add_subparsers(help='description', metavar='COMMAND', title='commands')

    parser_unpack = subparsers.add_parser('unpack', help='unpack .zip archive')
    parser_unpack.add_argument('archive', type=str, help='input file')
    parser_unpack.set_defaults(what='unpack')

    parser_videos = subparsers.add_parser('videos', help='convert audio files to yt-uploadable videos')
    parser_videos.add_argument('dir', type=str, help='directory containing audio files')
    parser_videos.set_defaults(what='videos')

    args = parser.parse_args()
    #print args
    if args.what == 'unpack':
        unpack(args.archive, args.dry_run)
    elif args.what == 'videos':
        videos(args.dir, args.dry_run)
    else:
        assert False
