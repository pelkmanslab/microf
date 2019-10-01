from setuptools import setup

from mf.__version__ import __version__

setup(
    name='mf',
    version=__version__,
    packages=['mf'],
    entry_points={
        'console_scripts': ['mf=mf.__main__:main'],
    },
    ## metadata for PyPI uploads
    description='Miscellaneous image file utilities',
    url='https://github.com/pelkmanslab/mf.git',
    author=', '.join([
        'Diego Villamaina',
        'Riccardo Murri',
    ]),
    author_email=', '.join([
        'diego.villamaina@gmail.com',
        'riccardo.murri@gmail.com',
    ]),
    license='MIT',
    # `zip_safe` can ease deployment, but is only allowed if the package
    # do *not* do any __file__/__path__ magic nor do they access package data
    # files by file name (use `pkg_resources` instead).
    zip_safe=True,
)
