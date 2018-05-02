#!/usr/bin/env python

# Convert tif to png and rename files from IC6000 to CV7000 file format
import argparse
import os
import re
from utils import walker
import renamef as rnf
import convertf as cnf


def rename_func(args, microscope=rnf.IC6000):
    pattern = re.compile(microscope['pattern'], re.I)
    replace_fn = microscope['replace']
    channels = microscope['channels']
    ignored=0
    renamed=0
    for path in build_path_list(args.path):
        image_name = os.path.basename(path)
        match = pattern.search(image_name)
        if match:
            params = match.groupdict()
            exp_name, well, site, channel = replace_fn(params, channels)
            if args.check:
                print image_name
                print rnf.CV7000.format(exp_name,well,site,channel)
                print
            else:
                old = path
                new = os.path.join(
                    os.path.dirname(path),
                    rnf.CV7000.format(exp_name, well, site, channel))
                os.rename(old,new)
                renamed += 1
        else:
            print image_name + ': Pattern does not match, ignored!'
            print
            ignored += 1
    print "Finished.. {} renamed, {} ignored".format(renamed,ignored)


def convert_func(args):
    for source_filepath in build_path_list(args.path):
        name = os.path.basename(source_filepath)
        _, ext = os.path.splitext(source_filepath)
        if ext.lower() in ['tif', 'tiff']:
            cnf.run_convert(source_filepath)
            if not args.keep:
                os.remove(source_filepath)


def main():

    parser = argparse.ArgumentParser(description='Convert .tif to .png and rename IC6000 files to CV7000 format')
    subparsers = parser.add_subparsers()

    rename = subparsers.add_parser('rename', help='Rename files')
    rename.add_argument('path', nargs='+', help='Path(s) of the files or directory to rename')
    rename.add_argument('--check', '-check', action='store_true', help='Check conversion before renaming')
    rename.set_defaults(func=rename_func)  # set the default function to sync

    convert = subparsers.add_parser('convert', help='Convert files')
    convert.add_argument('path', nargs='+', help='Path(s) of the files or directory containing the .tif files to convert to .png')
    convert.add_argument('--keep', '-keep', action='store_true', help='Keeps original files')
    convert.set_defaults(func=convert_func)  # set the default function to sync

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
     main()
