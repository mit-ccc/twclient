'''
End-to-end integration test of functionality
'''

import os
import hashlib
import warnings

import pytest
assert hasattr(pytest.mark, 'vcr')

from src.twclient._cli.entrypoint import cli

from . import utils as ut


_TARGET_ARGS = (
    '-n', 'wwbrannon', 'CCCatMIT', 'RTFC_Boston', 'cortico',
    '-l', '214727905'
)

_CASSETTE_FILE = 'cassettes/twclient/end-to-end.yaml'

# sqlalchemy made several breaking changes in version 2.0; let's see the
# warnings about them if using an earlier version
os.environ['SQLALCHEMY_WARN_20'] = '1'


# see anything that's potentially a problem or is deprecated
warnings.filterwarnings('always')


@pytest.fixture(scope="module")
def vcr_config():  # pylint: disable=missing-function-docstring
    return {
        'filter_headers': ['authorization'],
        'record_mode': 'none',
    }


def make_commands(dct, auth, target_args=_TARGET_ARGS):
    '''
    Make command sequence for end-to-end test
    '''

    frc = ['-c', str(dct / 'twclientrc.tmp')]
    fdb = ['-d', 'db']
    fai = ['-a', 'api']

    conf = frc + fdb

    # program name is passed separately
    commands = [
        ['config', 'add-api',
            '-k', auth['CONSUMER_KEY'],
            '-m', auth['CONSUMER_SECRET'],
            'api'
        ] + frc,
        ['config', 'add-db', '-f', str(dct / 'scratch.db'), 'db'] + frc,

        ['initialize', '-d', 'db', '-y'] + conf,
        ['tag', 'create', 'users'] + conf,

        ['fetch', 'users'] + target_args + conf + fai,
        ['tag', 'apply', 'users'] + target_args + conf,

        ['fetch', 'tweets', '-g', 'users'] + conf + fai,
        ['fetch', 'friends', '-g', 'users'] + conf + fai,
        ['fetch', 'followers', '-g', 'users'] + conf + fai,

        ['export', 'follow-graph', '-o', str(dct / 'follow-graph.csv')] + conf,
        ['export', 'mention-graph', '-o', str(dct / 'mention-graph.csv')] + conf,
        ['export', 'retweet-graph', '-o', str(dct / 'retweet-graph.csv')] + conf,
        ['export', 'reply-graph', '-o', str(dct / 'reply-graph.csv')] + conf,
        ['export', 'quote-graph', '-o', str(dct / 'quote-graph.csv')] + conf,
        ['export', 'tweets', '-o', str(dct / 'tweets.csv')] + conf,
        ['export', 'user-info', '-o', str(dct / 'user-info.csv')] + conf,
        ['export', 'mutual-followers', '-o', str(dct / 'mutual-followers.csv')] + conf,
        ['export', 'mutual-friends', '-o', str(dct / 'mutual-friends.csv')] + conf,
    ]

    return {  # pylint: disable=line-too-long
        'commands': commands,
        'artifacts': {
            str(dct / 'follow-graph.csv'): '08e41beaf34ab619d14b83221f41a975c69f14f9c3244218a7211455496eda48',
            str(dct / 'mention-graph.csv'): '88feb9e7e28f4ca1c4fd1a37fdaa8482bcb407a98b90a203465f4e69513a5e90',
            str(dct / 'retweet-graph.csv'): '8e611260875d3f8ec5de3cedf3178c9e2b7ed5578ce66edcec1b8830fa1d52d1',
            str(dct / 'reply-graph.csv'): '379809a4a8ddc45cbaee470f1edcd32e98a56d066719ee16f9a824f45e45f634',
            str(dct / 'quote-graph.csv'): '7aecb467be3e200c4c7d8f051327ac6ab2f1316e9c1a86f63efea6fa31f7bc96',
            str(dct / 'tweets.csv'): 'e032e29008bcef814e7b259852f53d6ff83bf412a07ffd9f251e32d7d1813e43',
            str(dct / 'user-info.csv'): 'b73338c9aeeb182885b15ed330016190567405eeb7f83ad674dc410f6b1dc5da',
            str(dct / 'mutual-followers.csv'): '81085039adb01c328969bc4ac087426536da8a2172f2d2f19d4e06184c242e81',
            str(dct / 'mutual-friends.csv'): '2087c305023d79d4f92ac80771ef2cc2b4dd0cdea26370e6453df5cd64f70967',
        },
    }


@pytest.mark.vcr(_CASSETTE_FILE)
def test_end_to_end(tmp_path):
    '''
    End-to-end integration test of twclient functionality
    '''

    if not os.path.exists(_CASSETTE_FILE):
        pytest.skip('Cassette file not found')
    if 'CONSUMER_KEY' not in os.environ:
        pytest.skip('Twitter API credentials not found')
    if 'CONSUMER_SECRET' not in os.environ:
        pytest.skip('Twitter API credentials not found')

    auth = {
        'CONSUMER_KEY': os.environ['CONSUMER_KEY'],
        'CONSUMER_SECRET': os.environ['CONSUMER_SECRET'],
    }

    dat = make_commands(tmp_path, auth)

    for cmd in dat['commands']:
        cli(prog='twclient', args=cmd)

    for fname, val in dat['artifacts'].items():
        checksum = hashlib.sha256()

        with open(fname, 'rb') as fil:
            for chunk in ut.chunk_read(fil, chunk_size=4096):
                checksum.update(chunk)

        assert checksum.hexdigest() == val
