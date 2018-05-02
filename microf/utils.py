import os

def walker(directory_path):
    '''Helper. Walk through the root directory tree
     Yield all files'''
    for dirpath, dirnames, filenames in os.walk(directory_path):
        for filename in filenames:
            yield os.path.join(dirpath,filename)


def build_path_list(paths):
    """
    """
    cwd = os.getcwd()
    result = []
    for path in paths:
        if not os.path.isabs(path):
            path = os.path.join(cwd, path)
        if os.path.isdir(path):
            result.extend(walker(path))
        else:
            result.append(path)
    return result
