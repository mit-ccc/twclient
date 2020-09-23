#!/usr/bin/env python3

'''
twclient: A high-level analytics-focused client for the Twitter API
'''

import os

from setuptools import setup, find_packages

import twclient  # for version

# FIXME do something about the sql files in docs

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
    name='twclient',
    version=twclient.__version__,
    author='William Brannon',
    author_email='wbrannon@mit.edu',
    url='https://github.com/wwbrannon/twclient',
    # license='', # FIXME and create LICENSE file

    description='A high-level analytics-focused client for the Twitter API',
    long_description=long_description,
    long_description_content_type='text/markdown',

    project_urls={
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
            'twitter=twclient.cli:cli',
        ]
    },

    platforms=['any'],
    keywords=['twitter', 'tweepy', 'data science', 'analytics'],
    classifiers=[
        'Development Status :: 4 - Beta',

        # 'License :: OSI Approved :: MIT License', # FIXME

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules'

        'Operating System :: OS Independent',

        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ]
)
