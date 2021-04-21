#!/usr/bin/env python3

'''
twclient: A high-level analytics-focused client for the Twitter API
'''

# FIXME do something about the sql files in docs
# FIXME license param to setup(), create LICENSE file, license classifier

# See docs at:
# https://packaging.python.org/guides/distributing-packages-using-setuptools/

import os

from setuptools import setup, find_packages

import twclient  # for version

HERE = os.path.dirname(os.path.abspath(__file__))
README = os.path.join(HERE, 'README.md')
CHANGELOG = os.path.join(HERE, 'CHANGELOG.md')

with open(README, encoding='utf-8', mode='rt') as f:
    readme_text = f.read().strip()

with open(CHANGELOG, encoding='utf-8', mode='rt') as f:
    changelog_text = f.read().strip()

long_description = readme_text + '\n\n' + changelog_text

install_deps = [
    'tweepy',
    'sqlalchemy'
]

extras = {
    'test': [
        'coverage',
        'pytest'
    ]
}

setup(
    name='twclient',
    version=twclient.__version__,
    author='William Brannon',
    author_email='wbrannon@mit.edu',
    url='https://github.com/wwbrannon/twclient',
    # license='',

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

    install_requires=install_deps,
    extras_require=extras,

    entry_points={
        'console_scripts': [
            'twitter=twclient.cli:cli',
        ]
    },

    platforms=['any'],
    keywords=['twitter', 'tweepy', 'data science', 'analytics'],
    classifiers=[
        'Development Status :: 4 - Beta',

        # 'License :: OSI Approved :: MIT License',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules'

        'Operating System :: OS Independent',

        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ]
)
