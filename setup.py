#!/usr/bin/env python3

import os

from setuptools import setup, find_packages

import twbeta # for version

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, 'README.md'), encoding='utf-8', mode='rt') as f:
    long_description = f.read()

# https://packaging.python.org/guides/distributing-packages-using-setuptools/
setup(
    name='twbeta', # FIXME and s/twbeta/twclient/ here and in code
    version=twbeta.__version__, # FIXME update this
    url='https://github.com/wwbrannon/twclient',
    # license='', # FIXME
    author='William Brannon',
    author_email='wbrannon@mit.edu',

    description='A high-level analytics-focused client for the Twitter API',
    long_description=long_description,
    long_description_content_type='text/markdown',

    project_urls = { # FIXME
    },

    zip_safe=True,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[ # FIXME versions?
        'tweepy',
        'sqlalchemy'
    ],

    entry_points={
        'console_scripts': [
            'twbeta=twbeta.cli:cli',
        ]
    },

    keywords=[],

    platforms=['any'],
    classifiers=[
        'Development Status :: 3 - Alpha',

        # 'License :: OSI Approved :: MIT License', # FIXME

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules'

        'Operating System :: OS Independent',

        'Programming Language :: Python',
        'Programming Language :: Python :: 2', # FIXME?
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',

    ]
)

