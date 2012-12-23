#!/bin/env python

import os
from distutils.core import setup

name = 'smartfile'
version = '1.0'
release = '1'
versrel = version + '-' + release
readme = os.path.join(os.path.dirname(__file__), 'README.rst')
download_url = 'https://github.com/downloads/smartfile/client-python/' \
                           '/' + name + '-' + versrel + '.tar.gz'
long_description = file(readme).read()

setup(
    name = name,
    version = versrel,
    description = 'A Python client for the SmartFile API.',
    long_description = long_description,
    requires = [
        'requests',
    ],
    author = 'SmartFile',
    author_email = 'info@smartfile.com',
    maintainer = 'Ben Timby',
    maintainer_email = 'btimby@gmail.com',
    url = 'http://github.com/smartfile/client-python/',
    download_url = download_url,
    license = 'MIT',
    packages=['smartfile'],
    package_data={'': ['README.rst']},
    classifiers = (
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
