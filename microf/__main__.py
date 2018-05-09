#!/usr/bin/env python
#
# pylint: disable=fixme,line-too-long

from __future__ import absolute_import, division, print_function

"""
Micro File manipulation utility.

* Convert TIFF files to PNG
* Rename files from IC6000 to CV7000 file format.

"""

import argparse
from itertools import izip_longest
import logging
import os
from os.path import basename, exists, isabs, isdir, join, splitext
import re
from subprocess import call, check_call, CalledProcessError
import sys
from tempfile import NamedTemporaryFile


## microscope file format data

CV7000 = '{}_{}_T0001F{}L01A01Z01C{}.tif'

def _IC6000_replace(params, channels):
    """
    Extract metadata from filename.

    These are examples of filenames that can be parsed::

        C_13_fld_2_wv_405_Blue.tif
        20180328_TestAbs_G - 8(fld 4 wv Red - Cy5).tif
    """
    exp_name = params['n'].replace("_","")
    well_letter = params['w'].replace(" ","").split('-')[0]
    well_number = params['w'].replace(" ","").split('-')[1].zfill(2)
    site = str(params['s'].zfill(3))
    channel = channels[params['c'].replace(" ","")]
    return exp_name, well_letter+well_number, site, channel

IC6000 = {
    'pattern': r'(?P<n>.*_.*)_(?P<w>[A-Z]\D*\d*)\(fld\D*(?P<s>\d*)\D*wv(?P<c>.*)\).(tif|png)',
    'channels': {
        'UV-DAPI':     '01',
        'Blue-FITC':   '02',
        'Green-dsRed': '03',
        'Red-Cy5':     '04',
    },
    'replace': _IC6000_replace,
}


## utility functions

def build_file_list(paths):
    """
    """
    cwd = os.getcwd()
    result = []
    for path in paths:
        if not exists(path):
            logging.error("Path `%s` does not exist, ignoring.", path)
            continue
        if not isabs(path):
            path = join(cwd, path)
        if isdir(path):
            result.extend(walker(path))
        else:
            result.append(path)
    return result


# taken from the "recipes" section of
# Python's `itertools` documentation
def grouper(iterable, size, fillvalue=None):
    """
    Collect data into fixed-length chunks or blocks.

    Example::

      >>> for chunk in grouper('ABCDEFG', 3, 'x'):
      ...   print(chunk)
      ('A', 'B', 'C')
      ('D', 'E', 'F')
      ('G', 'x', 'x')
    """
    args = [iter(iterable)] * size
    return izip_longest(*args, fillvalue=fillvalue)


def submit_to_slurm(cmds, size=1200, prefix=None):
    if prefix is None:
        stem, _ = splitext(basename(sys.argv[0]))
        prefix = stem
    if not prefix.endswith('.'):
        prefix += '.'
    with NamedTemporaryFile(
            prefix=prefix, suffix='.sh', delete=True) as script:
        script.write("""#!/bin/sh
#SBATCH -c 1
#SBATCH --mem-per-cpu=256m
#SBATCH --time={minutes}
#SBATCH --output={cwd}/{prefix}%A_%a.log
#SBATCH --error={cwd}/{prefix}%A_%a.log

case "$SLURM_ARRAY_TASK_ID" in
        """.format(
            cwd=os.getcwd(),
            minutes=int(1 + (5.0 * size)/60),
            prefix=prefix,
        ))
        for n, batch in enumerate(grouper(cmds, size, None)):
            print("  {n})".format(n=n), file=script)
            print("    set -e -x", file=script)
            for cmd in batch:
                print("    {cmd}".format(cmd=cmd), file=script)
            print("    exit 0;;", file=script)
        script.write("""
esac

echo 1>&2 "Array job ID $SLURM_ARRAY_TASK_ID not matched in script"
exit 70  # EX_SOFTWARE
""")
        # ensure everything is actually written to disk
        script.flush()
        # now submit job array
        call(['sbatch', '--array=0-{n}'.format(n=n), script.name])



def quote(arg):
    return "'{}'".format(arg)


def run(cmds, just_print=True, batch=0, verb=None):
    if verb is None:
        verb = splitext(basename(sys.argv[0]))
    if just_print:
        # print commands but don't run them
        for cmd in cmds:
            print(cmd)
    elif batch:
        submit_to_slurm(cmds, batch, prefix=verb)
    else:
        # immediate action
        done = 0
        errored = 0
        for cmd in cmds:
            try:
                check_call(cmd, shell=True)
                done += 1
            except CalledProcessError:
                errored += 1
        print(
            "Successfully applied {verb} to {done} files,"
            " {errored} errors."
            .format(verb=verb, done=done, errored=errored))


def walker(path):
    """
    Iterate over all file names in the directory tree rooted at *path*.
    """
    # pylint: disable=unused-variable
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            yield join(dirpath, filename)


## main

def rename_func(args, microscope=IC6000):
    pattern = re.compile(microscope['pattern'], re.I)
    replace_fn = microscope['replace']
    channels = microscope['channels']

    ignored = 0
    inbox = build_file_list(args.path)

    # filter out those which don't match the given pattern
    to_do = []
    for path in inbox:
        image_name = os.path.basename(path)
        match = pattern.search(image_name)
        if match:
            to_do.append(path)
        else:
            logging.warn(image_name + ': Pattern does not match, ignored!')
            ignored += 1
    print("Examined {total} files: {to_do} to rename, {ignored} ignored."
          .format(total=len(inbox), to_do=len(to_do), ignored=ignored))

    if to_do:
        # build list of commands
        fmt = "mv '{old}' '{new}'"
        cmds = []
        for path in to_do:
            image_name = os.path.basename(path)
            match = pattern.search(image_name)
            params = match.groupdict()
            exp_name, well, site, channel = replace_fn(params, channels)
            old = path
            new = os.path.join(
                os.path.dirname(path),
                CV7000.format(exp_name, well, site, channel))
            cmds.append(fmt.format(old=old, new=new))

        run(cmds, args.check, args.batch, 'rename')


def convert_func(args):
    ignored = 0
    inbox = build_file_list(args.path)

    # filter out those which don't match the given pattern
    to_do = []
    for path in inbox:
        stem, ext = os.path.splitext(path)
        if ext.lower() in ['.tif', '.tiff']:
            to_do.append((
                # source file name
                path,
                # destination file name
                stem + '.png',
            ))
        else:
            print (path + ': no TIFF extension, ignored!')
            ignored += 1
    print ("Examined {total} files: {to_do} to convert, {ignored} ignored."
           .format(total=len(inbox), to_do=len(to_do), ignored=ignored))

    if to_do:
        fmt = "convert -depth 16 -colorspace gray '{old}' '{new}'"
        if not args.keep:
            fmt += "; rm -f '{old}'"
        cmds = []
        for old, new in to_do:
            cmds.append(fmt.format(old=old, new=new))

        run(cmds, args.check, args.batch, 'convert')


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)8s: %(message)s',
    )

    parser = argparse.ArgumentParser(
        description='Convert .tif to .png and rename IC6000 files to CV7000 format')
    subparsers = parser.add_subparsers()

    rename = subparsers.add_parser('rename', help='Rename files')
    rename.add_argument('path', nargs='+', help='Path(s) of the files or directory to rename')
    rename.add_argument('--batch', '-batch', nargs='?', metavar='NUM',
                        action='store', type=int, default=0, const=1200,
                        help=(
                            'Submit rename job to SLURM cluster in batches of NUM images.'
                            ' If this option is *not* specified, images will be processed one by one;'
                            ' if NUM is not given, process images in batches of 1200.'))
    rename.add_argument('--check', '-check', action='store_true', help='Check conversion before renaming')
    rename.set_defaults(func=rename_func)  # set the default function to sync

    convert = subparsers.add_parser('convert', help='Convert files')
    convert.add_argument('path', nargs='+', help='Path(s) of the files or directory containing the .tif files to convert to .png')
    convert.add_argument('--keep', '-keep', action='store_true', help='Keeps original files')
    convert.add_argument('--check', '-check', action='store_true', help='Print commands but do not execute them')
    convert.add_argument('--batch', '-batch', nargs='?', metavar='NUM',
                         action='store', type=int, default=0, const=1200,
                         help=(
                             'Submit rename job to SLURM cluster in batches of NUM images.'
                             ' If this option is *not* specified, images will be processed one by one;'
                             ' if NUM is not given, process images in batches of 1200.'))
    convert.set_defaults(func=convert_func)  # set the default function to sync

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
