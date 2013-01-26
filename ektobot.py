#!/usr/bin/python

import os
import zipfile
import argparse

def parse_name(filename):
    parts = filename.split(' - ')
    return (parts[0], parts[1])

def dir_name(filename):
    parsed = parse_name(filename)
    return parsed[0].replace(' ', '_') + '_-_' + parsed[1].replace(' ', '_') + '/'

def unpack(args):
    #print 'unpack', args
    dirname = dir_name(args.archive)
    if not args.dry_run:
        os.mkdir(dirname)

    zipf = zipfile.ZipFile(args.archive, 'r')
    print 'Extracting {0} to {1} ...'.format(args.archive, dirname)
    if not args.dry_run:
        zipf.extractall(dirname)

    return dirname

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument('-n', '--dry-run', action='store_true', help='only print what will be done')
    subparsers = parser.add_subparsers(help='description', metavar='COMMAND', title='commands')

    parser_unpack = subparsers.add_parser('unpack', help='unpack .zip archive')
    parser_unpack.add_argument('archive', type=str, help='input file')
    parser_unpack.set_defaults(func=unpack)

    args = parser.parse_args()
    #print args
    args.func(args)
