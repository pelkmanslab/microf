#!/usr/bin/env python

# Convert tif to png and rename files from IC6000 to CV7000 file format
import argparse
import os
import re
from utils import walker 
import renamef as rnf
import convertf as cnf


def rename_func(args, microscope=rnf.IC6000):
    ignored=0
    renamed=0
    os.chdir(args.dir)
    #pattern = re.compile(rnf.microscope['pattern'])
    pattern = re.compile(microscope['pattern'])
    for path_to_file in walker(os.getcwd()):
        image_name = os.path.basename(path_to_file)
        match = pattern.search(image_name)
        if match:
            params = match.groupdict()
            #exp_name,well,site,channel = rnf.microscope['replace'](params, rnf.microscope['channels'])
            exp_name,well,site,channel = rnf.microscope['replace'](params, rnf.microscope['channels'])
            if args.check:
                print image_name
                print rnf.CV7000.format(exp_name,well,site,channel)
                print
            else:
                old = path_to_file
                new = os.path.join(os.path.dirname(path_to_file),rnf.CV7000.format(exp_name,well,site,channel))
                os.rename(old,new)
                renamed+=1
        else:
            print image_name + ': Patter does not match, ignored!'
            print
            ignored+=1
    print "Finished.. {} renamed {} ignored".format(renamed,ignored)


def convert_func(args):
    os.chdir(args.dir)
    for source_filepath in walker(os.getcwd()):
        name = os.path.basename(source_filepath)
        if name.endswith('tif'):
            if args.keep:
                cnf.run_convert(source_filepath)
            else:
                cnf.run_convert(source_filepath)
                os.remove(source_filepath) 


def main():
    
    parser = argparse.ArgumentParser(description='Convert .tif to .png and rename IC6000 files to CV7000 format')
    subparsers = parser.add_subparsers()

    rename = subparsers.add_parser('rename', help='Rename files')
    rename.add_argument('dir', help='Full path to the directory containing the files to rename')
    rename.add_argument('-check', action='store_true', help='Check conversion before renaming')
    rename.set_defaults(func=rename_func)  # set the default function to sync

    convert = subparsers.add_parser('convert', help='Convert files')
    convert.add_argument('dir', help='Full path to the directory containing the .tif files to convert to .png')
    convert.add_argument('-keep', action='store_true', help='Keeps original files')
    convert.set_defaults(func=convert_func)  # set the default function to sync
    
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    
     main()
