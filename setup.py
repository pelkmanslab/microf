from setuptools import setup

setup(name='microf',
      version='0.1',
      description='Convert (tif -> png) and rename (IC600 -> CV7000) files',
      url='https://github.com/pelkmanslab/microf.git',
      author='Diego Villamaina',
      author_email='diego.villamaina@gmail.com',
      license='MIT',
      packages=['microf'],
      entry_points={
        'console_scripts': ['microf=microf.cli:main'],
      },
      zip_safe=False      
      )
