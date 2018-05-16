#!/usr/bin/env python
#
# pylint: disable=fixme,line-too-long

"""
Micro File manipulation utility.

* Convert TIFF files to PNG (with action `convert`)
* Rename files from IC6000 to CV7000 naming format (with action `rename`).

"""

from __future__ import absolute_import, division, print_function

import argparse
from itertools import izip_longest
import logging
import os
from os.path import basename, exists, isabs, isdir, join, splitext
import posix
import re
from subprocess import call, check_call, CalledProcessError
import sys
from tempfile import mkdtemp, NamedTemporaryFile


class Action(object):
    """
    Base class for all actions.

    Methods implemented in *this* class do nothing; derived classes
    need to provide their own implementation to actually produce an
    effect.
    """

    def __init__(self, opts):
        self._opts = opts

    def accept(self, filename):
        """
        Return a pair *(new, params)* specifying effects of running
        this action, or raise a `Action.Reject` exception to signal
        that the file should *not* be processed.

        It is assumed that the command built by the `process`:meth:
        will read data from the given *filename* and store processed
        data into file *new* (may be the same filename).  Second item
        *params* is a key/value mapping that will be addded to the
        global pipeline state (which is passed around in the
        `process`:meth: calls).

        By default, no transformation is applied to the filename
        (i.e., *filename* and *new* are exactly the same), and no
        additional parameters are defined.
        """
        return (filename, {})

    class Reject(RuntimeError):
        """
        Signal that a file cannot be processed by this action.

        The exception message gives a reason.
        """
        pass

    def process(self, fmts, **state):
        """
        Add actions to pair *(fmts, state)*.

        By default, no action is taken.  Override this method in
        derived classes to actually implement any functionality.
        """
        return (fmts, state)


class Mention(Action):
    """
    Insert a comment line indicating processing instructions for a certain file.
    """

    def process(self, fmts, **state):
        fmts.append("# '{old}' -> '{new}'")
        return (fmts, state)


class NewName(Action):
    """
    Make a link to the source file under a (possibly) new name.
    """

    def process(self, fmts, **state):
        if state['old'] != state['new']:
            fmts.append("ln -f '{old}' '{new}'")
        return (fmts, state)


class Remove(Action):
    """
    Remove original files after processing.
    """

    def process(self, fmts, **state):
        if not state['keep']:
            fmts.append("rm -f '{old}'")
        return (fmts, state)


class Rename(Action):
    """
    Rename files according to a user-specified pattern.
    """
    def __init__(self, opts):
        super(Rename, self).__init__(opts)
        if not opts.from_pattern or not opts.to_pattern:
            self._from_pattern = None
            self.to_pattern = None
        else:
            if opts.from_pattern.count('*') != opts.to_pattern.count('*'):
                raise RuntimeError(
                    "The patterns provided to `--from-pattern` and `--to-pattern`"
                    " do not contain the same number of `*` wildcard characters.")
            self.from_pattern = self._make_filename_re(opts.from_pattern)
            self.to_pattern = self._make_filename_fmt(opts.to_pattern)

    def _make_filename_re(self, glob_pattern):
        return re.compile(self._make_star_pattern(
            glob_pattern, r'(?P<wildcard{0}>.*)', re.escape))

    def _make_filename_fmt(self, glob_pattern):
        return self._make_star_pattern(
            glob_pattern, r'{{wildcard{0}}}', lambda arg: arg)

    @staticmethod
    def _make_star_pattern(glob_pattern, star_fmt, escape):
        glob_pattern, ext = split_image_extension(glob_pattern)
        parts = glob_pattern.split('*')
        num_stars = len(parts) - 1
        stars = [star_fmt.format(n)
                 for n in range(num_stars)]
        fmt = (
            ''.join(
                ''.join([escape(parts[n]), stars[n]])
                for n in range(num_stars)
            ) + parts[-1] + ext
        )
        return fmt

    def accept(self, filename):
        if self.from_pattern is None:
            return (filename, {})
        match = self.from_pattern.match(filename)
        if not match:
            raise self.Reject(
                "File name `{0}` does not match pattern"
                " provided with `--from-pattern`"
                .format(filename))
        params = match.groupdict()
        new = self.to_pattern.format(**params)
        return (new, params)


class TiffToPng(Action):
    """
    Convert TIFF files to PNG.
    """

    name = 'tiff-to-png'

    def accept(self, filename):
        stem, ext = os.path.splitext(filename)
        if ext.lower() in ['.tif', '.tiff']:
            return (
                # destination file name
                stem + '.png',
                # additional state
                {}
            )
        else:
            raise self.Reject("not a TIFF file")

    def process(self, fmts, **state):
        fmts.append("convert -depth 16 -colorspace gray '{old}' '{new}'")
        return (fmts, state)


class IC6kToCV7k(Action):
    """
    Convert file names from the pattern used on IC6000 to Yokogawa's CV7000.
    """

    name = 'ic6k-to-cv7k'

    def accept(self, filename):
        match = self._ic6000_pattern.match(filename)
        if not match:
            raise self.Reject(
                "file name does not match the configured IC6000 pattern")
        # extract metadata from the file name
        try:
            old_md = match.groupdict()
            new_md = {}
            new_md['experiment_name'] = (old_md['date'] + '_' + old_md['name'])
            new_md['well_letter'] = old_md['well_letter']
            new_md['well_nr'] = int(old_md['well_nr'])
            new_md['site'] = int(old_md['site'])
            new_md['channel'] = self._ic6000_channels[old_md['channel_tag']]
        except Exception as err:
            raise RuntimeError(
                "Cannot parse file name `{0}` with IC6000 pattern: {1}"
                .format(filename, err))
        return (
            # destination
            self._cv7000_fmt.format(**new_md),
            # additional state
            new_md
        )

    _cv7000_fmt = '{experiment_name}_{well_letter}{well_nr:02d}_T0001F{site:03d}L01A01Z01C{channel:02d}.tif'

    # FIXME: this pattern seems specific to the current configuration
    # of the IC6000 at PelkmansLab
    _ic6000_pattern = re.compile(
        (
            # example pattern to match:
            #
            #   20180328_TestAbs_G - 8(fld 4 wv Red - Cy5).tif
            #
            r'(?P<date>[0-9]{8})_'
            r'(?P<name>[^_]+)_'
            r'(?P<well_letter>[A-Z]+) - (?P<well_nr>[0-9]+)'
            r'\('
            r'fld (?P<site>[0-9]+)'
            r' wv (?P<channel_color>[A-Za-z]+) - (?P<channel_tag>.+)'
            r'\)'
            r'\.'
        ),
        #'(?P<w>[A-Z]\D*\d*)\(fld\D*(?P<s>\d*)\D*wv(?P<c>.*)\).(tif|png)',
        re.I)

    # FIXME: like the above, this pattern seems specific to the
    # current configuration of the IC6000 at PelkmansLab
    _ic6000_channels = {
        'DAPI':  1,
        'FITC':  2,
        'dsRed': 3,
        'Cy5':   4,
    }


## utility functions

def build_path_list(paths):
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
            result.extend(listdir_recursive(path))
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


def listdir_recursive(path):
    """
    Iterate over all file names in the directory tree rooted at *path*.
    """
    # pylint: disable=unused-variable
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            yield join(dirpath, filename)


def quote(arg):
    return "'{}'".format(arg)


def run(cmds, just_print=True, batch=0, verb=None):
    if verb is None:
        verb, _ = splitext(basename(sys.argv[0]))
        if verb == '__main__':
            verb = 'process'
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


def split_image_extension(filename):
    stem, ext = splitext(filename)
    if ext.lower() in [
            '.jpg', '.jpeg'
            '.png',
            '.tiff', '.tif',
    ]:
        return (stem, ext)
    else:
        return (filename, '')


def submit_to_slurm(cmds, size=200, prefix=None):
    if prefix is None:
        stem, _ = splitext(basename(sys.argv[0]))
        prefix = stem
    if not prefix.endswith('.'):
        prefix += '.'

    # NOTE: we need the `jobdir` directory to be visible (under the
    # same path) from both submission and worker nodes -- let's just
    # assume that the current working directory has this property
    cwd = os.getcwd()
    jobdir = mkdtemp(dir=cwd, prefix=prefix, suffix='.d')
    for n, batch in enumerate(grouper(cmds, size, None)):
        array_task_job = '{0}/{1}{2}.sh'.format(jobdir, prefix, n)
        with open(array_task_job, 'w') as script:
            script.write("""#! /bin/sh

# print commands e(x)ecuted and (e)xit on first error
set -e -x
            """)
            for cmd in batch:
                # `grouper(..., None)` will right-pad the shorter
                # batches with `None`, to ensure all batches have the
                # required length.  So if we hit `None`, we know
                # enumeration of commands ends here.
                if cmd is None:
                    break
                print("{cmd}".format(cmd=cmd), file=script)
            script.write("""
# remove this script so that...
rm -f {array_task_job}

# ...the last-run script will succeed in removing the (now empty) directory
rmdir -v --ignore-fail-on-non-empty {array_task_job}

# if we get to this point, all went well
exit 0
            """.format(
                array_task_job=array_task_job
            ))
            # ensure everything is actually written to disk
            script.flush()

    with NamedTemporaryFile(
            prefix=prefix, suffix='.sh', delete=True) as script:
        script.write("""#!/bin/sh
#SBATCH -c 1
#SBATCH --mem-per-cpu=256m
#SBATCH --time={minutes}
#SBATCH --output={cwd}/{prefix}%A_%a.log
#SBATCH --error={cwd}/{prefix}%A_%a.log

exec /bin/sh {jobdir}/{prefix}"$SLURM_ARRAY_TASK_ID".sh "$@"
        """.format(
            cwd=cwd,
            jobdir=jobdir,
            minutes=int(1 + (5.0 * size)/60),
            prefix=prefix,
        ))
        # ensure everything is actually written to disk
        script.flush()

        # now submit job array
        call(['sbatch', '--array=0-{n}'.format(n=n), script.name])


def xor(a, b):
    return bool(a) ^ bool(b)


## main

def build_pipeline(args):
    actions = [
        Mention(args)
    ]
    # apply microscope metadata conversion before anything else
    if args.rename:
        actions.append(IC6kToCV7k(args))
    # user-specified rename
    if args.from_pattern:
        actions.append(Rename(args))
    if args.convert:
        actions.append(TiffToPng(args))
    elif args.rename:
        actions.append(NewName(args))
    if not args.keep:
        actions.append(Remove(args))
    return actions


def do_actions(actions, args):
    # build list of files to process
    ignored = 0
    inbox = build_path_list(args.path)
    to_do = {}
    for path in inbox:
        filename = basename(path)
        state = {
            'old': filename,
            'check': args.check,
            'keep': args.keep,
        }
        for action in actions:
            try:
                new, params = action.accept(filename)
            except Action.Reject as err:
                logging.info("Ignoring file `%s`: %s", path, err)
                ignored += 1
                break
            state.update(params)
            filename = new
        else:
            state['new'] = filename
            to_do[path] = state
    print(
        "Examined {total} files: {to_do} to convert, {ignored} ignored."
        .format(total=len(inbox), to_do=len(to_do), ignored=ignored))

    # build and run list of commands
    if to_do:
        cmds = []
        for path, state in to_do.iteritems():
            fmts = []
            for action in actions:
                fmts, state = action.process(fmts, **state)
            cmd = '\n'.join(fmt.format(**state) for fmt in fmts)
            cmds.append(cmd)
        run(cmds, args.check, args.batch)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)8s: %(message)s',
    )


def parse_command_line(argv):
    cmdline = argparse.ArgumentParser(description=__doc__)
    cmdline.add_argument('path', nargs='+',
                         help=('Path(s) of the files or directory on which to act.'))
    cmdline.add_argument('--batch', '-batch', '-b',
                         action='store_true', default=False,
                         help=(
                             'Submit action to SLURM cluster in batches.'
                             ' If this option is *not* specified,'
                             ' images will be processed one by one.'
                             ' The batch size can be controlled'
                             ' with option `--batch-size`.'))
    cmdline.add_argument('--batch-size', metavar='NUM',
                         action='store', type=int, default=200,
                         help=(
                             'Process images in independent batches of size NUM on a cluster.'
                             ' Only used in conjunction with option `--batch`.'
                             ' if NUM is not given, process images in batches of 200.'))
    cmdline.add_argument('--check', '-check', '--just-print', '-n',
                         action='store_true', default=False,
                         help='Print commands but do not execute them.')
    cmdline.add_argument('--convert', action='store_true', default=False,
                         help='Convert TIFF images to 16-bit grayscale PNG.')
    cmdline.add_argument('--from-pattern', '-f',
                         action='store', default='', metavar='PATTERN',
                         help=("Pattern that input files must match."
                               " Every occurrence of the `*` character"
                               " here can match any (possibly empty)"
                               " sequence of characters, which will be"
                               " preserved in the 'to' pattern;"
                               " anything else will be replaced"
                               " with the corresponding string"
                               " in the pattern given by"
                               " the `---to-pattern` option."
                               " NOTE: no `.tif` or `.png` or similar"
                               " extension should be given in the pattern"
                               " --it will be automatically added."))
    cmdline.add_argument('--keep', '-keep', action='store_true',
                         help="Do not delete original files.")
    cmdline.add_argument('--rename', action='store_true', default=False,
                         help=("Rename image files"
                               " from the IC6000 naming convention"
                               " to the Yokogawa CV7000 one."))
    cmdline.add_argument('--to-pattern', '-t',
                         action='store', default='', metavar='PATTERN',
                         help=("Pattern to produce output file names."
                               " Every occurrence of the `*` character"
                               " here will be substituted with the"
                               " (possibly empty) sequence matched by"
                               " the original filename in the pattern"
                               " given to the `--from-pattern` option."
                               " NOTE: no `.tif` or `.png` or similar"
                               " extension should be given in the pattern"
                               " --it will be automatically added."))

    args = cmdline.parse_args(argv)

    if args.path[0] == 'convert':
        logging.warning(
            "Please add `--convert` on the command-line"
            " instead of writing `convert` as first file name.")
        args.convert = True
        del args.path[0]
    elif args.path[0] == 'rename':
        logging.warning(
            "Please add `--rename` on the command-line"
            " instead of writing `rename` as first file name.")
        args.rename = True
        del args.path[0]

    if not (args.convert or args.rename):
        cmdline.error(
            "At least one of options `--convert` or `--rename` should be given.")

    if xor(args.from_pattern, args.to_pattern):
        cmdline.error(
            "If one of options `--from-pattern` or `--to-pattern` is given,"
            " then the other must be given as well.")

    return args


def main(argv):
    setup_logging()
    args = parse_command_line(argv)
    actions = build_pipeline(args)
    do_actions(actions, args)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
