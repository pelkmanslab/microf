from itertools import izip_longest
import os
from os.path import isabs, isdir, join


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


def walker(path):
    """
    Iterate over all file names in the directory tree rooted at *path*.
    """
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            yield join(dirpath, filename)
