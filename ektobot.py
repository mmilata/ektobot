#!/usr/bin/python

import os
import os.path
import zipfile
import argparse
import subprocess

def parse_name(filename):
    parts = filename.split(' - ')
    return (parts[0], parts[1])

def dir_name(filename):
    parsed = parse_name(filename)
    return parsed[0].replace(' ', '_') + '_-_' + parsed[1].replace(' ', '_') + '/'

def run(args):
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    if p.returncode != 0:
        raise RuntimeError('Subprocess failed w/ return code {0}, stderr:\n {1}')

def unpack(archive, dry_run):
    #print 'unpack', args
    dirname = dir_name(archive)
    if not dry_run:
        os.mkdir(dirname)

    zipf = zipfile.ZipFile(archive, 'r')
    print 'Extracting {0} to {1} ...'.format(archive, dirname)
    if not dry_run:
        zipf.extractall(dirname)

    return dirname

def videos(dirname, dry_run, outdir=None):
    if not outdir:
        outdir = dirname
    if not os.path.isdir(outdir):
        print 'Creating output directory {0}'
        os.mkdir(outdir)

    files = os.walk(dirname).next()[2]
    mp3s = sorted(filter(lambda f: f.endswith('.mp3'), files))
    #mp3s = map(lambda f: os.path.join(dirname, f), mp3s)
    cover = os.path.join(dirname, 'folder.jpg')
    if not os.path.exists(cover):
        raise RuntimeError('Cover {0} not found'.format(cover))
    print 'Using image {0} as a cover'.format(cover)
    for infile in mp3s:
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
        except:
            print 'Converting {0} failed'.format(infile)
            raise
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
