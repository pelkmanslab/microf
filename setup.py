from setuptools import setup

setup(
    name='microf',
    version='0.7.0',
    packages=['microf'],
    entry_points={
        'console_scripts': ['mf=microf:main'],
    },
    ## metadata for PyPI uploads
    description='Miscellaneous image file utilities',
    url='https://github.com/pelkmanslab/microf.git',
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
