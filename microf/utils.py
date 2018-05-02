from itertools import izip_longest
import os
from os.path import isabs, isdir, join

def walker(directory_path):
    '''Helper. Walk through the root directory tree
     Yield all files'''
    for dirpath, dirnames, filenames in os.walk(directory_path):
        for filename in filenames:
            yield join(dirpath, filename)


# taken from the "recipes" section of
# Python's `itertools` documentation
def grouper(iterable, size, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF G
    args = [iter(iterable)] * size
    return izip_longest(*args, fillvalue=fillvalue)


def build_path_list(paths):
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
