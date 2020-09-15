#!/usr/bin/env python3

import os

from setuptools import setup, find_packages

import twbeta # for version

HERE = os.path.dirname(os.path.abspath(__file__))
README = os.path.join(HERE, 'README.md')
CHANGES = os.path.join(HERE, 'CHANGES.md')

with open(README, encoding='utf-8', mode='rt') as f:
    readme_text = f.read().strip()

with open(README, encoding='utf-8', mode='rt') as f:
    changes_text = f.read().strip()

long_description = readme_text + '\n\n' + changes_text

# https://packaging.python.org/guides/distributing-packages-using-setuptools/
setup(
    name='twbeta', # FIXME and s/twbeta/twclient/ here and in code
    version=twbeta.__version__,
    author='William Brannon',
    author_email='wbrannon@mit.edu',
    url='https://github.com/wwbrannon/twclient',
    # license='', # FIXME

    description='A high-level analytics-focused client for the Twitter API',
    long_description=long_description,
    long_description_content_type='text/markdown',

    project_urls = {
        'Source Code': 'https://github.com/wwbrannon/twclient',
        'Bug Tracker': 'https://github.com/wwbrannon/twclient/issues',
        # 'Documentation': '',
    },

    zip_safe=True,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'tweepy',
        'sqlalchemy'
    ],

    entry_points={
        'console_scripts': [
            'twbeta=twbeta.cli:cli',
        ]
    },

    platforms=['any'],
    keywords=['twitter', 'tweepy', 'data science', 'analytics'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        # 'License :: OSI Approved :: MIT License', # FIXME

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules'

        'Operating System :: OS Independent',

        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ]
)

