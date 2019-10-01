from setuptools import setup

setup(
    name='mf',
    version='1.0.2',
    py_modules=['mf'],
    entry_points={
        'console_scripts': ['mf=mf:main'],
    },
    # `zip_safe` can ease deployment, but is only allowed if the package
    # do *not* do any __file__/__path__ magic nor do they access package data
    # files by file name (use `pkg_resources` instead).
    zip_safe=True,
    ## metadata for PyPI uploads
    description='Simple image file utilities',
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
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
)
