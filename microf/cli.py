#!/usr/bin/env python
#
# pylint: disable=fixme,line-too-long

from __future__ import absolute_import, division, print_function

# Convert tif to png and rename files from IC6000 to CV7000 file format
import argparse
import os
import re
from subprocess import check_call
import sys

from utils import build_file_list, grouper
import renamef as rnf
import convertf as cnf


def rename_func(args, microscope=rnf.IC6000):
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
            print (image_name + ': Pattern does not match, ignored!')
            ignored += 1
    print ("Examined {total} files: {to_do} to rename, {ignored} ignored."
           .format(total=len(inbox), to_do=len(to_do), ignored=ignored))

    def dofiles(paths, action):
        done = 0
        for path in paths:
            image_name = os.path.basename(path)
            match = pattern.search(image_name)
            params = match.groupdict()
            exp_name, well, site, channel = replace_fn(params, channels)
            old = path
            new = os.path.join(
                os.path.dirname(path),
                rnf.CV7000.format(exp_name, well, site, channel))
            try:
                action(old, new)
                done += 1
            except Exception:
                # FIXME: silently ignores error, should log it!
                pass
        return done

    if to_do:
        if args.check:
            def do_check(old, new):
                print ("{old} -> {new}".format(
                    old=os.path.basename(old),
                    new=os.path.basename(new),
                ))
            dofiles(to_do, do_check)
        elif args.batch:
            from tempfile import NamedTemporaryFile
            for batch in grouper(to_do, args.batch, ''):
                # pylint: disable=bad-continuation
                with NamedTemporaryFile(
                        prefix='renamef.',
                        suffix='.sh',
                        delete=True) as script:
                    script.write("""#!/bin/sh
                    {exe} {me} {batch}
                    """.format(
                        exe=sys.executable,
                        me=sys.argv[0],
                        # FIXME: this will break if files have any spaces in the name
                        batch=' '.join(batch),
                    ))
                    script.flush()
                    check_call(["sbatch", script.name])
        else:
            # rename immediately
            renamed = dofiles(to_do, os.rename)
            print ("Renamed {renamed} files.".format(renamed=renamed))


def convert_func(args):
    ignored = 0
    inbox = build_file_list(args.path)

    # filter out those which don't match the given pattern
    to_do = []
    for path in inbox:
        _, ext = os.path.splitext(path)
        if ext.lower() in ['tif', 'tiff']:
            to_do.append(path)
        else:
            print (path + ': no TIFF extension, ignored!')
            ignored += 1
    print ("Examined {total} files: {to_do} to convert, {ignored} ignored."
           .format(total=len(inbox), to_do=len(to_do), ignored=ignored))

    if to_do:
        if args.batch:
            from tempfile import NamedTemporaryFile
            for batch in grouper(to_do, args.batch, ''):
                # pylint: disable=bad-continuation
                with NamedTemporaryFile(
                        prefix='convertf.',
                        suffix='.sh',
                        delete=True) as script:
                    script.write("""#!/bin/sh
                    {exe} {me} {batch}
                    """.format(
                        exe=sys.executable,
                        me=sys.argv[0],
                        # FIXME: this will break if files have any spaces in the name
                        batch=' '.join(batch),
                    ))
                    script.flush()
                    check_call(["sbatch", script.name])
        else:
            # convert immediately
            for source_filepath in to_do:
                cnf.run_convert(source_filepath)
                if not args.keep:
                    os.remove(source_filepath)


def main():

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
