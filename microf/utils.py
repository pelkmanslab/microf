import os

def walker(directory_path):
    '''Helper. Walk through the root directory tree
     Yield all files'''
    for dirpath, dirnames, filenames in os.walk(directory_path):
        for filename in filenames:
            yield os.path.join(dirpath,filename)


