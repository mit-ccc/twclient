#!/usr/bin/env python3

# FIXME update logging stuff, esp use __repr__ method on exceptions

"""
The command-line interface script
"""

import os, sys
import logging
import argparse as ap
import collections as cl
import configparser as cp

import tweepy
from sqlalchemy import create_engine

from . import job
from . import error as err
from . import models as md
from . import target as tg
from . import twitter_api as ta

logger = logging.getLogger(__name__)

def parse_config_file(args, parser):
    config = cp.ConfigParser(dict_type=cl.OrderedDict)
    config.read(os.path.expanduser(args.config_file))

    # preserve order
    profiles = [x for x in config.keys() if x != 'DEFAULT']

    err_string = 'Malformed configuration file: '

    for s in profiles:
        if 'type' not in config[s].keys():
            msg = 'Section {0} missing type declaration field'
            parser.error(err_string + msg.format(s))

        if config[s]['type'] not in ('database', 'api'):
            msg = 'Section {0} must have "type" of either "api" or "database"'
            parser.error(err_string + msg.format(s))

    db_profiles = [x for x in profiles if config[x]['type'] == 'database']
    for profile in db_profiles:
        try:
            assert profile in config.keys()
            assert config[profile]['type'] == 'database'

            assert 'is_default' in config[profile].keys()
            assert 'database_url' in config[profile].keys()
        except AssertionError:
            parser.error(err_string + 'Bad DB profile {0}'.format(profile))

    try:
        assert sum([
            config.getboolean(p, 'is_default')
            for p in db_profiles
        ]) <= 1
    except AssertionError:
        parser.error(err_string + 'Need at most one DB profile marked default')

    api_profiles = [x for x in profiles if config[x]['type'] == 'api']
    for profile in api_profiles:
        try:
            assert profile in config.keys()
            assert config[profile]['type'] == 'api'

            assert 'consumer_key' in config[profile].keys()
            assert 'consumer_secret' in config[profile].keys()

            assert not ( \
                'token' in config[profile].keys() and \
                not 'token_secret' in config[profile].keys() \
            )

            assert not ( \
                'token_secret' in config[profile].keys() and \
                not 'token' in config[profile].keys() \
            )
        except AssertionError:
            parser.error(err_string + 'Bad API profile {0}'.format(profile))

    return config

def get_selected_db_profile(args, parser, config):
    db_profiles = [
        key
        for key in config.keys()
        if key != 'DEFAULT' and config[key]['type'] == 'database'
    ]

    api_profiles = [
        key
        for key in config.keys()
        if key != 'DEFAULT' and config[key]['type'] == 'api'
    ]

    if args.database is not None:
        if args.database in api_profiles:
            msg = 'Profile {0} is not a DB profile'
            parser.error(msg.format(args.database))
        elif args.database not in db_profiles:
            msg = 'Profile {0} not found'
            parser.error(msg.format(args.database))
        else:
            db_to_use = args.database
    elif len(db_profiles) > 0:
        db_to_use = db_profiles[-1] # order in the file is preserved
    else:
        parser.error('No database profiles configured (use add-db)')

    return create_engine(config[db_to_use]['database_url'])

def get_selected_api(args, parser, config):
    api_profiles = [
        key
        for key in config.keys()
        if key != 'DEFAULT' and config[key]['type'] == 'api'
    ]

    if args.apis is not None:
        profiles_to_use = args.apis
    else:
        profiles_to_use = api_profiles

    auths = []
    for p in profiles_to_use:
        if 'token' in config[p].keys():
            auth = tweepy.OAuthHandler(
                config[p]['consumer_key'],
                config[p]['consumer_secret']
            )

            auth.set_access_token(config[p]['token'], config[p]['secret'])
        else:
            auth = tweepy.AppAuthHandler(
                config[p]['consumer_key'],
                config[p]['consumer_secret']
            )

        auths += [auth]

    if len(auths) == 0:
        parser.error('No Twitter credentials provided (use `config add-api`)')

    return ta.TwitterApi(auths=auths, abort_on_bad_targets=args.abort_on_bad_targets)

def get_selected_targets(args, parser, config):
    targets = []

    if args.user_ids is not None:
        targets += [tg.UserIdTarget(targets=args.user_ids)]
    if args.screen_names is not None:
        targets += [tg.ScreenNameTarget(targets=args.screen_names)]
    if args.select_tag is not None:
        targets += [tg.SelectTagTarget(targets=args.select_tag)]
    if args.twitter_lists is not None:
        targets += [tg.TwitterListTarget(targets=args.twitter_lists)]

    if len(targets) == 0:
        parser.error('No target users provided')

    return targets

def cli_config(args, parser, config):
    assert args.command == 'config'

    db_profiles = [
        key
        for key in config.keys()
        if key != 'DEFAULT' and config[key]['type'] == 'database'
    ]

    api_profiles = [
        key
        for key in config.keys()
        if key != 'DEFAULT' and config[key]['type'] == 'api'
    ]

    profiles = db_profiles + api_profiles
    config_file = os.path.expanduser(args.config_file)

    if args.subcommand == 'list-db':
        for s in db_profiles:
            if args.full:
                print('[' + s + ']')
                for k, v in config[s].items():
                    print(k + ' = ' + v)
                print('\n')
            else:
                print(s)
    elif args.subcommand == 'list-api':
        for s in api_profiles:
            if args.full:
                print('[' + s + ']')
                for k, v in config[s].items():
                    print(k + ' = ' + v)
                print('\n')
            else:
                print(s)
    elif args.subcommand == 'rm-db':
        if args.name not in profiles:
            msg = 'DB profile {0} not found'
            parser.error(msg.format(args.name))
        elif args.name in api_profiles:
            parser.error('Profile {0} is an API profile'.format(args.name))
        else:
            if config.getboolean(args.name, 'is_default'):
                for n in db_profiles:
                    if n != args.name:
                        config[n]['is_default'] = True
                        break

            config.pop(args.name)

        with open(config_file, 'wt') as f:
            config.write(f)
    elif args.subcommand == 'rm-api':
        if args.name not in profiles:
            msg = 'API profile {0} not found'
            parser.error(msg.format(args.name))
        elif args.name in db_profiles:
            parser.error('Profile {0} is a DB profile'.format(args.name))
        else:
            config.pop(args.name)

        with open(config_file, 'wt') as f:
            config.write(f)
    elif args.subcommand == 'add-db':
        if args.name == 'DEFAULT':
            parser.error('Profile name may not be "DEFAULT"')
        elif args.name in profiles:
            parser.error('Profile {0} already exists'.format(args.name))

        if args.file:
            url = 'sqlite:///' + args.file
        else:
            url = args.database_url

        config[args.name] = {
            'type': 'database',
            'is_default': len(db_profiles) == 0,
            'database_url': url
        }

        with open(config_file, 'wt') as f:
            config.write(f)
    elif args.subcommand == 'add-api':
        if args.name == 'DEFAULT':
            parser.error('Profile name may not be "DEFAULT"')
        elif args.name in profiles:
            msg = 'Profile {0} already exists'
            parser.error(msg.format(args.name))
        else:
            config[args.name] = {
                'type': 'api',
                'consumer_key': args.consumer_key,
                'consumer_secret': args.consumer_secret
            }

            if args.token is not None:
                config[args.name]['token'] = args.token

            if args.token_secret is not None:
                config[args.name]['token_secret'] = args.token_secret

        with open(config_file, 'wt') as f:
            config.write(f)
    elif args.subcommand == 'set-db-default':
        if args.name not in profiles:
            msg = 'DB profile {0} not found'
            parser.error(msg.format(args.name))
        elif args.name in api_profiles:
            parser.error('Profile {0} is an API profile'.format(args.name))
        else:
            for n in db_profiles:
                if config.getboolean(n, 'is_default'):
                    config[n]['is_default'] = False

                config[args.name]['is_default'] = True

        with open(config_file, 'wt') as f:
            config.write(f)
    else:
        parser.error('Bad subcommand to cli_config')

def cli_tag(args, parser, config, engine):
    assert args.command == 'tag'

    if args.subcommand == 'create':
        job.CreateTagJob(tag=args.name, engine=engine).run()
    elif args.subcommand == 'delete':
        job.DeleteTagJob(tag=args.name, engine=engine).run()
    elif args.subcommand == 'apply':
        targets = get_selected_targets(args, parser, config)

        job.ApplyTagJob(tag=args.name, targets=targets, engine=engine).run()
    else:
        parser.error('Bad subcommand to cli_tag')

def cli_initialize(args, parser, engine):
    if not args.yes:
        logger.warning("WARNING: This command will drop the Twitter data "
                        "schema and delete all data! If you want to "
                        "proceed, rerun with '-y'.")
    else:
        logger.warning('Recreating schema and dropping existing data')

        md.Base.metadata.drop_all(engine)
        md.Base.metadata.create_all(engine)

def cli():
    ##
    ## Parse arguments
    ##

    desc = 'Fetch Twitter data and store in a DB schema'
    parser = ap.ArgumentParser(description=desc)

    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='verbosity level (repeat for more)')
    parser.add_argument('-c', '--config-file', default='~/.twbetarc',
                        help='path to config file (default ~/.twbetarc)')

    def add_target_arguments(p):
        # selecting users to operate on
        p.add_argument('-g', '--select-tag', nargs='+',
                       help='process loaded users with these tags')
        p.add_argument('-i', '--user-ids', nargs='+',
                       help='process particular Twitter user IDs')
        p.add_argument('-n', '--screen-names', nargs='+',
                       help='process particular Twitter screen names')
        p.add_argument('-l', '--twitter-lists', nargs='+',
                       help='process all users in particular Twitter lists')

        return p

    sp = parser.add_subparsers(dest='command')
    sp.required = True

    config_subparser = sp.add_parser('config', help='manage configuration')
    config = config_subparser.add_subparsers(dest='subcommand')

    ## Config file handling

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
    aap.add_argument('-c', '--consumer-secret', required=True,
                     help='consumer secret')
    aap.add_argument('-t', '--token', help='OAuth token')
    aap.add_argument('-s', '--token-secret', help='OAuth token secret')

    rap = config.add_parser('rm-api', help='remove Twitter API profile')
    rap.add_argument('name', help='name of API profile to remove')

    ## User tagging

    tag_subparser = sp.add_parser('tag', help='manage user tags')
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
    tap = add_target_arguments(tap)
    tap.add_argument('name', help='the name of the tag')
    tap.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')

    ## Other arguments

    inp = sp.add_parser('initialize', help='Initialize the DB schema '
                                           '(WARNING: deletes all data!)')
    inp.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')
    inp.add_argument('-y', '--yes', action='store_true',
                     help='Must specify this option to initialize')

    uip = sp.add_parser('hydrate', help='Get user info / "hydrate" users')
    uip = add_target_arguments(uip)
    uip.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')
    uip.add_argument('-a', '--api', dest='apis', nargs='+',
                     help='use only these stored API profiles instead ' \
                          'of default')
    uip.add_argument('-b', '--abort-on-bad-targets', action='store_true',
                     help="abort if a requested user doesn't exist")


    frp = sp.add_parser('friends', help="Get user friends (may load new users)")
    frp = add_target_arguments(frp)
    frp.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')
    frp.add_argument('-a', '--api', dest='apis', nargs='+',
                     help='use only these stored API profiles instead ' \
                          'of default')
    frp.add_argument('-b', '--abort-on-bad-targets', action='store_true',
                     help="abort if a requested user doesn't exist")

    flp = sp.add_parser('followers', help="Get user followers (may load new users)")
    flp = add_target_arguments(flp)
    flp.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')
    flp.add_argument('-a', '--api', dest='apis', nargs='+',
                     help='use only these stored API profiles instead ' \
                          'of default')
    flp.add_argument('-b', '--abort-on-bad-targets', action='store_true',
                     help="abort if a requested user doesn't exist")

    twp = sp.add_parser('tweets', help="Get user tweets (may load new users")
    twp = add_target_arguments(twp)
    twp.add_argument('-d', '--database',
                     help='use this stored DB profile instead of default')
    twp.add_argument('-a', '--api', dest='apis', nargs='+',
                     help='use only these stored API profiles instead ' \
                          'of default')
    twp.add_argument('-b', '--abort-on-bad-targets', action='store_true',
                     help="abort if a requested user doesn't exist")
    twp.add_argument('-o', '--old-tweets', action='store_true',
                     help="Load tweets older than user's most recent in DB")
    twp.add_argument('-c', '--since-timestamp',
                     help='ignore tweets older than this Unix timestamp')
    twp.add_argument('-r', '--max-tweets',
                     help='max number of tweets to collect')

    args = parser.parse_args()

    ##
    ## Set up logging
    ##

    if args.verbose == 0:
        lvl = logging.WARNING
    elif args.verbose == 1:
        lvl = logging.INFO
    else: # verbose >= 2
        lvl = logging.DEBUG

    fmt = '%(asctime)s : %(module)s : %(levelname)s : %(message)s'
    logging.basicConfig(format=fmt, level=lvl)

    ##
    ## Commands: interact with config file
    ##

    config = parse_config_file(args, parser)

    if args.command == 'config':
        try:
            return cli_config(args, parser, config)
        except err.TWClientError as e:
            if logging.getLogger().getEffectiveLevel() == logging.WARNING:
                logger.error(e.message)
            else:
                logger.exception(e.message)

            sys.exit(e.exit_status)

    ##
    ## Commands: database-only
    ##

    engine = get_selected_db_profile(args, parser, config)

    if args.command == 'tag':
        try:
            return cli_tag(args, parser, config, engine)
        except err.TWClientError as e:
            if logging.getLogger().getEffectiveLevel() == logging.WARNING:
                logger.error(e.message)
            else:
                logger.exception(e.message)
            sys.exit(e.exit_status)

    if args.command == 'initialize':
        try:
            return cli_initialize(args, parser, engine)
        except err.TWClientError as e:
            if logging.getLogger().getEffectiveLevel() == logging.WARNING:
                logger.error(e.message)
            else:
                logger.exception(e.message)

            sys.exit(e.exit_status)

    ##
    ## Commands: fetch Twitter data
    ##

    api = get_selected_api(args, parser, config)
    targets = get_selected_targets(args, parser, config)

    ## Massage the arguments a bit for passing on to job classes
    command = vars(args).pop('command')

    to_drop = ['abort_on_bad_targets', 'verbose', 'database', 'apis',
                'config_file', 'yes',

                'select_tag', 'user_ids', 'screen_names', 'twitter_lists']

    for v in to_drop:
        vars(args).pop(v, None)

    vars(args)['engine'] = engine
    vars(args)['api'] = api
    vars(args)['targets'] = targets

    ## Actually run jobs
    cls = {
        'hydrate': job.UserInfoJob,
        'friends': job.FriendsJob,
        'followers': job.FollowersJob,
        'tweets': job.TweetsJob
    }[command]

    try:
        return cls(**vars(args)).run()
    except err.TWClientError as e:
        if logging.getLogger().getEffectiveLevel() == logging.WARNING:
            logger.error(e.message)
        else:
            logger.exception(e.message)

        sys.exit(e.exit_status)

if __name__ == '__main__':
    cli()

