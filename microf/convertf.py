import os
from subprocess import check_call, check_output, CalledProcessError

def replace_ext(filename, ext):
        """
        Return new pathname formed by replacing extension in `filename` with `ext`.
        """
        if ext.startswith('.'):
            ext = ext[1:]
        stem, _ = os.path.splitext(filename)
        return (stem + '.' + ext)

def run_convert(source_filepath, ext='png'):
        final_filepath = replace_ext(source_filepath, ext)
        print 'converting file: {} to .png'.format(source_filepath)
        check_call(
            ['convert', source_filepath, '-depth', '16',
            '-colorspace', 'gray', final_filepath])


