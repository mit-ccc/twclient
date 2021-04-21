#!/usr/bin/env python3

"""
The command-line interface script
"""

import logging
import argparse as ap

from .command import _ConfigCommand, _TagCommand, _InitializeCommand, \
                     _FetchCommand

logger = logging.getLogger(__name__)


def _add_target_arguments(parser):
    parser.add_argument('-w', '--randomize', action='store_true',
                        help='randomize processing order of targets')

    # selecting users to operate on
    parser.add_argument('-g', '--select-tags', nargs='+',
                        help='process loaded users with these tags')
    parser.add_argument('-i', '--user-ids', nargs='+', type=int,
                        help='process particular Twitter user IDs')
    parser.add_argument('-n', '--screen-names', nargs='+',
                        help='process particular Twitter screen names')
    parser.add_argument('-l', '--twitter-lists', nargs='+',
                        help='process all users in particular Twitter lists '
                             '(list ID or owner/slug)')

    return parser


def _add_fetch_arguments(parser):
    parser = _add_target_arguments(parser)

    parser.add_argument('-d', '--database',
                        help='use this stored DB profile instead of default')
    parser.add_argument('-a', '--api', dest='apis', nargs='+',
                        help='use only these stored API profiles instead '
                             'of default')
    parser.add_argument('-b', '--allow-api-errors', action='store_true',
                        help="continue even if an object to be fetched from "
                             "the Twitter API is protected or doesn't exist")

    return parser


def _make_parser():  # pylint: disable=too-many-statements,too-many-locals
    desc = 'Fetch Twitter data and store in a DB schema'
    parser = ap.ArgumentParser(description=desc)

    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='verbosity level (repeat for more)')
    parser.add_argument('-c', '--config-file', default='~/.twclientrc',
                        help='path to config file (default ~/.twclientrc)')

    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    config_subparser = subparsers.add_parser('config',
                                             help='Manage configuration')
    config = config_subparser.add_subparsers(dest='subcommand')

    #
    # Config file handling
    #

    # Database commands
    ldp = config.add_parser('list-db', help='list database profiles')
    ldp.add_argument('-f', '--full', action='store_true',
                     help='print all profile info')

    adp = config.add_parser('add-db', help='add DB profile')
    adp.add_argument('name', help='name to use for DB profile')
    grp = adp.add_mutually_exclusive_group(required=True)
    grp.add_argument('-u', '--database-url', help='database connection url')
    grp.add_argument('-f', '--file', help='sqlite database file path')

    rdp = config.add_parser('rm-db', help='remove DB profile')
    rdp.add_argument('name', help='name of DB profile to remove')

    sddp = config.add_parser('set-db-default', help='make DB profile default')
    sddp.add_argument('name', help='name of DB profile')

    # API commands
    lap = config.add_parser('list-api', help='list Twitter API profiles')
    lap.add_argument('-f', '--full', action='store_true',
                     help='print all profile info')

    aap = config.add_parser('add-api', help='add Twitter API profile')
    aap.add_argument('name', help='name of API profile')
    aap.add_argument('-k', '--consumer-key', required=True,
                     help='consumer key')
    aap.add_argument('-m', '--consumer-secret', required=True,
                     help='consumer secret')
    aap.add_argument('-t', '--token', help='OAuth token')
    aap.add_argument('-s', '--token-secret', help='OAuth token secret')

    rap = config.add_parser('rm-api', help='remove Twitter API profile')
    rap.add_argument('name', help='name of API profile to remove')

    #
    # User tagging
    #

    tag_subparser = subparsers.add_parser('tag', help='Manage user tags')
    tag = tag_subparser.add_subparsers(dest='subcommand')

    tcp = tag.add_parser('create', help='create a user tag')
    tcp.add_argument('name', help='the name of the tag')
    tcp.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')

    tdp = tag.add_parser('delete', help='delete a user tag')
    tdp.add_argument('name', help='the name of the tag')
    tdp.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')

    tap = tag.add_parser('apply', help='apply a tag to users')
    tap = _add_target_arguments(tap)
    tap.add_argument('name', help='the name of the tag')
    tap.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')
    tap.add_argument('-p', '--allow-missing-targets', action='store_true',
                     help="continue even if a requested target should be "
                          "present in the database but isn't")

    #
    # (Re-)initializing the database schema
    #

    inp = subparsers.add_parser('initialize',
                                help='Initialize the DB schema (WARNING: '
                                     'deletes all data!)')
    inp.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')
    inp.add_argument('-y', '--yes', action='store_true',
                     help='Must specify this option to initialize')

    #
    # Fetching Twitter data
    #

    fetch_subparser = subparsers.add_parser('fetch', help='Fetch Twitter data')
    fetch = fetch_subparser.add_subparsers(dest='subcommand')

    uip = fetch.add_parser('users', help='Get user info / "hydrate" users')
    uip = _add_fetch_arguments(uip)

    frp = fetch.add_parser('friends', help="Get user friends")
    frp = _add_fetch_arguments(frp)
    frp.add_argument('-p', '--allow-missing-targets', action='store_true',
                     help="continue even if a requested target should be "
                          "present in the database but isn't")
    frp.add_argument('-j', '--load-batch-size', type=int, default=None,
                     help='load data to DB in batches of this size (default '
                          'all at once), non-default values are slower but '
                          'reduce memory usage')

    flp = fetch.add_parser('followers', help="Get user followers")
    flp = _add_fetch_arguments(flp)
    flp.add_argument('-p', '--allow-missing-targets', action='store_true',
                     help="continue even if a requested target should be "
                          "present in the database but isn't")
    flp.add_argument('-j', '--load-batch-size', type=int, default=None,
                     help='load data to DB in batches of this size (default '
                          'all at once), non-default values are slower but '
                          'reduce memory usage')

    twp = fetch.add_parser('tweets', help="Get user tweets")
    twp = _add_fetch_arguments(twp)
    twp.add_argument('-p', '--allow-missing-targets', action='store_true',
                     help="continue even if a requested target should be "
                          "present in the database but isn't")
    twp.add_argument('-j', '--load-batch-size', type=int, default=None,
                     help='load data to DB in batches of this size (default '
                          'all at once), non-default values are slower but '
                          'reduce memory usage')
    twp.add_argument('-o', '--old-tweets', action='store_true',
                     help="Load tweets older than user's most recent in DB")
    twp.add_argument('-z', '--since-timestamp',
                     help='ignore tweets older than this Unix timestamp')
    twp.add_argument('-r', '--max-tweets',
                     help='max number of tweets to collect')

    return parser


def _log_setup(verbosity):
    if verbosity == 0:
        lvl = logging.WARNING
    elif verbosity == 1:
        lvl = logging.INFO
    else:  # verbosity >= 2
        lvl = logging.DEBUG

    fmt = '%(asctime)s : %(module)s : %(levelname)s : %(message)s'
    logging.basicConfig(format=fmt, level=lvl)

    logging.captureWarnings(True)


def cli():
    '''
    The main command-line entrypoint.

    This function is the main entrypoint, intended to be called by a user or
    script from the command line. It parses command-line arguments, sets up
    logging and delegates further processing to dedicated classes.

    Returns
    -------
    None
    '''

    parser = _make_parser()
    args = parser.parse_args()

    command = vars(args).pop('command')
    verbosity = vars(args).pop('verbose')

    _log_setup(verbosity)

    cls = {
        'config': _ConfigCommand,
        'tag': _TagCommand,
        'initialize': _InitializeCommand,
        'fetch': _FetchCommand
    }[command]

    cls(parser=parser, **vars(args)).run()


if __name__ == '__main__':
    cli()
