#!/usr/bin/env python3

from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='twclient',
    version='0.1.0',
    description='A high-level command-line client for the Twitter API',
    url='https://github.com/wwbrannon/twclient',
    author='William Brannon',
    author_email='will.brannon@gmail.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],

    packages=['twclient'],
    python_requires='>=3.7, <4',
    install_requires=['pyyaml', 'tweepy', 'psycopg2'],

    long_description=long_description,
    long_description_content_type='text/markdown',

    package_data={
        'twclient': ['sql/schema.sql'],
    },

    entry_points={
        'console_scripts': [
            'twitter=twclient.main:main',
        ],
    }
)

