from __future__ import absolute_import, division, print_function

from itertools import izip_longest
import os
from os.path import basename, isabs, isdir, join, splitext
from subprocess import call, check_call, CalledProcessError
import sys
from tempfile import NamedTemporaryFile


def build_file_list(paths):
    """
    """
    cwd = os.getcwd()
    result = []
    for path in paths:
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
            minutes=int(1 + (0.5 * size)/60),
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
        call(['sbatch', '--array=0-{top}'.format(top=n-1), script.name])



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
