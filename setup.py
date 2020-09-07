#!/usr/bin/env python3

from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='twbeta', # FIXME and s/twbeta/twclient/ in code
    version='0.1.0', # FIXME
    description='A high-level command-line client for the Twitter API',
    url='https://github.com/wwbrannon/twclient',
    author='William Brannon',
    author_email='wbrannon@mit.edu',
    classifiers=[
        # FIXME
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],

    packages=['twbeta'], # FIXME
    python_requires='>=3.7, <4', # FIXME revisit this?
    install_requires=['tweepy', 'sqlalchemy'],

    long_description=long_description,
    long_description_content_type='text/markdown',

    entry_points={
        'console_scripts': [
            'twbeta=twbeta.main:main', # FIXME
        ]
    }
)

