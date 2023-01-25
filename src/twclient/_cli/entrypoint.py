#!/usr/bin/env python3

'''
The command-line interface script.
'''

import logging
import argparse as ap

from .show import ShowCommand
from .fetch import FetchCommand
from .config import ConfigCommand
from .initialize import InitializeCommand
from .tag import TagCommand
from .export import ExportCommand

logger = logging.getLogger(__name__)


def _add_common_arguments(parser):
    parser.add_argument('-v', '--verbose', action='count', default=0,
        help='verbose output (use repeatedly for more verbosity)')
    parser.add_argument('-c', '--config-file', default='~/.twclientrc',
        help='path to config file (default ~/.twclientrc)')

    return parser


def _add_tag_arguments(parser):
    parser.add_argument('name', help='the name of the tag')
    parser.add_argument('-d', '--database',
                        help='use this stored DB profile instead of default')

    return parser


def _add_user_selection_arguments(parser):
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


def _add_export_arguments(parser):
    parser = _add_user_selection_arguments(parser)

    parser.add_argument('-d', '--database',
                        help='use this stored DB profile instead of default')
    parser.add_argument('-o', '--outfile',
                        help='write the export to this file (default stdout)')
    parser.add_argument('-p', '--allow-missing-targets', action='store_true',
                        help='continue even if a requested target should be '
                             'present in the database but isn''t')

    return parser


def _add_fetch_arguments(parser, extra=False):
    parser = _add_user_selection_arguments(parser)

    parser.add_argument('-w', '--randomize', action='store_true',
                        help='randomize processing order of targets')
    parser.add_argument('-d', '--database',
                        help='use this stored DB profile instead of default')
    parser.add_argument('-a', '--api', dest='apis', nargs='+',
                        help='use only these stored API profiles instead '
                             'of default')
    parser.add_argument('-b', '--allow-api-errors', action='store_true',
                        help="continue even if an object to be fetched from "
                             "the Twitter API is protected or doesn't exist")

    if extra:
        parser.add_argument('-p', '--allow-missing-targets',
                            action='store_true',
                            help='continue even if a requested target should '
                                 'be present in the database but isn''t')
        parser.add_argument('-j', '--load-batch-size', type=int, default=None,
                            help='load data to DB in batches of this size '
                                 '(default all at once), non-default values '
                                 'are slower but reduce memory usage')

    return parser


def _make_parser(prog=None):
    desc = 'Fetch Twitter data and store in a DB schema'
    parser = ap.ArgumentParser(prog=prog, description=desc)

    #
    # Commands
    #

    commands = parser.add_subparsers(dest='command')
    commands.required = True

    # command parsers
    cps = {
        'config': commands.add_parser('config', help='Manage configuration'),
        'tag': commands.add_parser('tag', help='Manage user tags'),
        'fetch': commands.add_parser('fetch', help='Fetch Twitter data'),
        'show': commands.add_parser('show', help='Print information'),
        'export': commands.add_parser('export', help='Export data'),
        'initialize': commands.add_parser('initialize',
            help='Initialize the DB schema (WARNING: deletes all data!)')
    }

    #
    # Subcommands
    #

    # subparsers objects for the command parsers
    sps = {
        key : val.add_subparsers(dest='subcommand')
        for key, val in cps.items()
        if key != 'initialize'
    }

    for key, val in sps.items():
        val.required = True

    # parsers for the command subparsers: subcommand parsers
    ssps = {}

    ssps['config'] = {
        'list-db':          sps['config'].add_parser('list-db',
                            help='list database profiles'),
        'add-db':           sps['config'].add_parser('add-db',
                            help='add DB profile'),
        'rm-db':            sps['config'].add_parser('rm-db',
                            help='remove DB profile'),
        'set-db-default':   sps['config'].add_parser('set-db-default',
                            help='make DB profile default'),
        'list-api':         sps['config'].add_parser('list-api',
                            help='list Twitter API profiles'),
        'add-api':          sps['config'].add_parser('add-api',
                            help='add Twitter API profile'),
        'rm-api':           sps['config'].add_parser('rm-api',
                            help='remove Twitter API profile')
    }

    ssps['tag'] = {
        'create':           sps['tag'].add_parser('create',
                            help='create a user tag'),
        'delete':           sps['tag'].add_parser('delete',
                            help='delete a user tag'),
        'apply':            sps['tag'].add_parser('apply',
                            help='apply a tag to users')
    }

    ssps['fetch'] = {
        'users':            sps['fetch'].add_parser('users',
                            help='Get user info / "hydrate" users'),
        'friends':          sps['fetch'].add_parser('friends',
                            help="Get user friends"),
        'followers':        sps['fetch'].add_parser('followers',
                            help="Get user followers"),
        'tweets':           sps['fetch'].add_parser('tweets',
                            help="Get user tweets")
    }

    ssps['show'] = {
        'ratelimit':        sps['show'].add_parser('ratelimit',
                            help='Report API keys'' rate limit status')
    }

    ssps['export'] = {
        'follow-graph':     sps['export'].add_parser('follow-graph',
                            help='Export follow graph'),
        'mention-graph':    sps['export'].add_parser('mention-graph',
                            help='Export mention graph'),
        'retweet-graph':    sps['export'].add_parser('retweet-graph',
                            help='Export retweet graph'),
        'reply-graph':      sps['export'].add_parser('reply-graph',
                            help='Export reply graph'),
        'quote-graph':      sps['export'].add_parser('quote-graph',
                            help='Export quote graph'),
        'tweets':           sps['export'].add_parser('tweets',
                            help='Export user tweets'),
        'user-info':        sps['export'].add_parser('user-info',
                            help='Export user-level data'),
        'mutual-followers': sps['export'].add_parser('mutual-followers',
                            help='Export all-pairs mutual follower counts'),
        'mutual-friends':   sps['export'].add_parser('mutual-friends',
                            help='Export all-pairs mutual friend counts')
    }

    #
    # Arguments
    #

    ## everything has these args
    _add_common_arguments(cps['initialize'])

    for subcmds in ssps.values():
        for subcmd in subcmds.values():
            _add_common_arguments(subcmd)

    ## initialize
    cps['initialize'].add_argument('-d', '--database',
                      help='use this stored DB profile instead of default')
    cps['initialize'].add_argument('-y', '--yes', action='store_true',
                      help='Must specify this option to initialize')

    ## export
    for subcmd in ['follow-graph', 'mention-graph', 'retweet-graph',
                   'reply-graph', 'quote-graph', 'tweets', 'user-info',
                   'mutual-followers', 'mutual-friends']:
        _add_export_arguments(ssps['export'][subcmd])

    ## fetch
    _add_fetch_arguments(ssps['fetch']['users'])
    _add_fetch_arguments(ssps['fetch']['friends'], extra=True)
    _add_fetch_arguments(ssps['fetch']['followers'], extra=True)
    _add_fetch_arguments(ssps['fetch']['tweets'], extra=True)

    ssps['fetch']['tweets'].add_argument('-o', '--old-tweets',
                                       action='store_true',
                                       help='Load tweets older than user''s '
                                            'most recent in DB')
    ssps['fetch']['tweets'].add_argument('-z', '--since-timestamp',
                     help='ignore tweets older than this Unix timestamp')
    ssps['fetch']['tweets'].add_argument('-r', '--max-tweets',
                     help='max number of tweets to collect')

    ## User tagging
    _add_tag_arguments(ssps['tag']['create'])
    _add_tag_arguments(ssps['tag']['delete'])
    _add_tag_arguments(ssps['tag']['apply'])

    _add_user_selection_arguments(ssps['tag']['apply'])
    ssps['tag']['apply'].add_argument('-p', '--allow-missing-targets',
                                      action='store_true',
                                      help='continue even if a requested '
                                           'targetshould be present in the '
                                           'database but isn''t')

    ## show
    ssps['show']['ratelimit'].add_argument('-f', '--full', action='store_true',
                            help='Output full json response from the '
                                 'Twitter API')

    grp = ssps['show']['ratelimit'].add_mutually_exclusive_group(required=False)
    grp.add_argument('-n', '--api-profile-name', dest='name',
                     help='API profile name')
    grp.add_argument('-k', '--consumer-key', help='consumer key')

    ## config db-*
    ssps['config']['list-db'].add_argument('-f', '--full', action='store_true',
                                         help='print all profile info')

    ssps['config']['add-db'].add_argument('name',
                                        help='name to use for DB profile')
    grp = ssps['config']['add-db'].add_mutually_exclusive_group(required=True)
    grp.add_argument('-u', '--database-url', help='database connection url')
    grp.add_argument('-f', '--file', help='sqlite database file path')

    ssps['config']['rm-db'].add_argument('name',
                                       help='name of DB profile to remove')

    ssps['config']['set-db-default'].add_argument('name',
                                                help='name of DB profile')

    ## config api-*
    ssps['config']['list-api'].add_argument('-f', '--full',
                                            action='store_true',
                                            help='print all profile info')

    ssps['config']['add-api'].add_argument('name', help='name of API profile')
    ssps['config']['add-api'].add_argument('-k', '--consumer-key',
                                         required=True, help='consumer key')
    ssps['config']['add-api'].add_argument('-m', '--consumer-secret',
                                         required=True, help='consumer secret')
    ssps['config']['add-api'].add_argument('-t', '--token', help='OAuth token')
    ssps['config']['add-api'].add_argument('-s', '--token-secret',
                                         help='OAuth token secret')

    ssps['config']['rm-api'].add_argument('name',
                                        help='name of API profile to remove')

    return parser


def cli(prog=None, args=None):
    '''
    The main command-line entrypoint.

    This function is the main entrypoint, intended to be called by a user or
    script from the command line. It parses command-line arguments, sets up
    logging and delegates further processing to dedicated classes.

    Returns
    -------
    None
    '''

    parser = _make_parser(prog=prog)
    args = parser.parse_args(args=args)

    command = vars(args).pop('command')
    verbosity = vars(args).pop('verbose')

    if verbosity == 0:
        lvl = logging.WARNING
    elif verbosity == 1:
        lvl = logging.INFO
    else:  # verbosity >= 2
        lvl = logging.DEBUG

    fmt = '%(asctime)s : %(module)s : %(levelname)s : %(message)s'
    logging.basicConfig(format=fmt, level=lvl)
    logging.captureWarnings(True)

    cls = {
        'config': ConfigCommand,
        'initialize': InitializeCommand,
        'fetch': FetchCommand,
        'show': ShowCommand,
        'tag': TagCommand,
        'export': ExportCommand
    }[command]

    cls(parser=parser, **vars(args)).run()


if __name__ == '__main__':
    cli()
