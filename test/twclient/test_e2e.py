'''
End-to-end integration test of functionality
'''

import os
import hashlib
import warnings

import pytest

from src.twclient._cli.entrypoint import cli

from . import utils as ut

# sqlalchemy made several breaking changes in version 2.0; let's see the
# warnings about them if using an earlier version
os.environ['SQLALCHEMY_WARN_20'] = '1'


# see anything that's potentially a problem or is deprecated
warnings.filterwarnings('always')


@pytest.fixture(scope="module")
def vcr_config():
    return {"filter_headers": ["authorization"]}


def make_commands(d):
    targets = [
        '-n', 'wwbrannon', 'CCCatMIT', 'RTFC_Boston', 'cortico',
        '-l', '214727905'
    ]

    frc = ['-c', str(d / 'twclientrc.tmp')]
    fdb = ['-d', 'db']
    fai = ['-a', 'api']

    conf = frc + fdb

    # program name is passed separately
    commands = [
        ['config', 'add-api',
            '-k', os.environ['CONSUMER_KEY'],
            '-m', os.environ['CONSUMER_SECRET'],
            'api'
        ] + frc,
        ['config', 'add-db', '-f', str(d / 'scratch.db'), 'db'] + frc,

        ['initialize', '-d', 'db', '-y'] + conf,
        ['tag', 'create', 'users'] + conf,

        ['fetch', 'users'] + targets + conf + fai,
        ['tag', 'apply', 'users'] + targets + conf,

        ['fetch', 'tweets', '-g', 'users'] + conf + fai,
        ['fetch', 'friends', '-g', 'users'] + conf + fai,
        ['fetch', 'followers', '-g', 'users'] + conf + fai,

        ['export', 'follow-graph', '-o', str(d / 'follow-graph.csv')] + conf,
        ['export', 'mention-graph', '-o', str(d / 'mention-graph.csv')] + conf,
        ['export', 'retweet-graph', '-o', str(d / 'retweet-graph.csv')] + conf,
        ['export', 'reply-graph', '-o', str(d / 'reply-graph.csv')] + conf,
        ['export', 'quote-graph', '-o', str(d / 'quote-graph.csv')] + conf,
        ['export', 'tweets', '-o', str(d / 'tweets.csv')] + conf,
        ['export', 'user-info', '-o', str(d / 'user-info.csv')] + conf,
        ['export', 'mutual-followers', '-o', str(d / 'mutual-followers.csv')] + conf,
        ['export', 'mutual-friends', '-o', str(d / 'mutual-friends.csv')] + conf,
    ]

    return {
        'commands': commands,
        'artifacts': {
            d / 'follow-graph.csv': '',
            d / 'mention-graph.csv': '',
            d / 'retweet-graph.csv': '',
            d / 'reply-graph.csv': '',
            d / 'quote-graph.csv': '',
            d / 'tweets.csv': '',
            d / 'user-info.csv': '',
            d / 'mutual-followers.csv': '',
            d / 'mutual-friends.csv': '',
        },
    }


@pytest.mark.vcr('cassettes/twclient/end-to-end.yaml')
def test_end_to_end(tmp_path):
    # dat = make_commands(tmp_path)
    import pathlib
    dat = make_commands(pathlib.Path('.'))

    for cmd in dat['commands']:
        cli(prog='twclient', args=cmd)

    for k, v in dat['artifacts'].items():
        checksum = hashlib.sha256()

        with open(k, 'rb') as f:
            for chunk in ut.chunk_read(f, chunk_size=4096):
                checksum.update(chunk)

        assert checksum.hexdigest() is not None  # FIXME == v
