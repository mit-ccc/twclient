#!/usr/bin/env python3

"""
The command-line interface script
"""

# FIXME should be able to specify Twitter data schema name
# FIXME option for copy/insert loading method

import os, sys
import logging
import argparse as ap
import collections as cl
import configparser as cp

import tweepy

import twclient.utils as ut

from sqlalchemy import create_engine

from twclient.models import Base
from twclient.job import InitializeJob, UserInfoJob, FollowJob, TweetsJob

logger = logging.getLogger(__name__)

def main():
    ##
    ## Parse arguments
    ##

    desc = 'Fetch Twitter data and store in a DB schema'
    parser = ap.ArgumentParser(description=desc)

    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='verbosity level (repeat for more)')

    parser.add_argument('-c', '--config-file', default='~/.twclientrc',
                        help='path to config file (default ~/.twclientrc)')
    parser.add_argument('-d', '--database',
                        help='use this stored DB profile instead of default')
    parser.add_argument('-a', '--api', dest='apis', nargs='+',
                        help='use only these stored API profiles instead ' \
                             'of default')

    sp = parser.add_subparsers(dest='command')
    sp.required = True

    ## Config file handling

    ldp = sp.add_parser('list-db', help='list database profiles')
    ldp.add_argument('-f', '--full', action='store_true',
                     help='print all profile info')

    lap = sp.add_parser('list-api', help='list Twitter API profiles')
    lap.add_argument('-f', '--full', action='store_true',
                     help='print all profile info')

    # see https://docs.sqlalchemy.org/en/13/dialects/postgresql.html#empty-dsn-connections-environment-variable-connections
    adp = sp.add_parser('add-db', help='add DB profile and make default')
    adp.add_argument('-n', '--name', required=True,
                     help='name to use for DB profile')
    adp.add_argument('-u', '--database-url', help='database connection url')

    aap = sp.add_parser('add-api', help='add Twitter API profile')
    aap.add_argument('-n', '--name', required=True, help='name of API profile')
    aap.add_argument('-k', '--consumer-key', required=True,
                     help='consumer key')
    aap.add_argument('-c', '--consumer-secret', required=True,
                     help='consumer secret')
    aap.add_argument('-t', '--token', help='OAuth token')
    aap.add_argument('-s', '--token-secret', help='OAuth token secret')

    rdp = sp.add_parser('rm-db', help='remove DB profile')
    rdp.add_argument('name', help='name of DB profile to remove')

    rap = sp.add_parser('rm-api', help='remove Twitter API profile')
    rap.add_argument('name', help='name of API profile to remove')

    ## Other arguments

    def common_arguments(sp):
        sp.add_argument('-u', '--user-tag',
                        help='tag to apply to any loaded / updated users')
        sp.add_argument('-b', '--abort-on-bad-targets', action='store_true',
                        help="abort if a requested user doesn't exist")
        sp.add_argument('-e', '--transaction', action='store_true',
                        help='load in one transaction')
        sp.add_argument('-z', '--load-batch-size',
                        help='run loads to DB in batches of this size')

        grp = sp.add_mutually_exclusive_group(required=True)
        grp.add_argument('-g', '--select-tag',
                         help='process only users with this tag')
        grp.add_argument('-i', '--user-ids', nargs='+',
                        help='get info for the given list of twitter user IDs')
        grp.add_argument('-n', '--screen-names', nargs='+',
                        help='get info for given list of twitter screen names')

        return sp, grp

    inp = sp.add_parser('initialize', help='Initialize the DB schema '
                                           '(WARNING: deletes all data!)')
    inp.add_argument('-y', '--yes', help='Must specify this option to initialize')

    uip = sp.add_parser('user_info', help='Get user info / "hydrate" users')
    uip, uipgrp = common_arguments(uip)
    uipgrp.add_argument('-l', '--twitter-lists', nargs='+',
                        help='get info for all users in given Twitter lists')

    frp = sp.add_parser('friends',
                        help="Get users' friends (may load new users rows)")
    frp, frpgrp = common_arguments(frp)
    frp.add_argument('-f', '--full', action='store_true',
                     help='Load full user objects (slower)')

    flp = sp.add_parser('followers',
                        help="Get users' followers (may load new users rows)")
    flp, flpgrp = common_arguments(flp)
    flp.add_argument('-f', '--full', action='store_true',
                     help='Load full user objects (slower)')

    twp = sp.add_parser('tweets',
                        help="Get users' tweets (may load new users rows")
    twp, twpgrp = common_arguments(twp)
    twp.add_argument('-o', '--old-tweets', action='store_true',
                     help="Load tweets older than user's most recent in DB")
    twp.add_argument('-c', '--since-timestamp',
                     help='ignore tweets older than this Unix timestamp')
    twp.add_argument('-r', '--max-tweets',
                     help='max number of tweets to collect')
    twp.add_argument('-f', '--full', action='store_true',
                     help='Load full user objects (slower)')
    twp.add_argument('-t', '--tweet-tag',
                     help='Tag to apply to loaded tweets')

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

    config_file = os.path.expanduser(args.config_file)

    config = cp.ConfigParser(dict_type=cl.OrderedDict)
    config.read(config_file)

    # preserve order
    profiles = [x for x in config.keys() if x != 'DEFAULT']

    for s in profiles:
        if 'type' not in config[s].keys():
            parser.error('Bad configuration file {0}: section missing '
                         'type declaration field'.format(s))

    db_profiles = [x for x in profiles if config[x]['type'] == 'database']
    api_profiles = [x for x in profiles if config[x]['type'] == 'api']

    if args.command == 'list-db':
        for s in db_profiles:
            if args.full:
                print('[' + s + ']')
                for k, v in config[s].items():
                    print(k + ' = ' + v)
                print('\n')
            else:
                print(s)

        return
    elif args.command == 'list-api':
        for s in api_profiles:
            if args.full:
                print('[' + s + ']')
                for k, v in config[s].items():
                    print(k + ' = ' + v)
                print('\n')
            else:
                print(s)

        return
    elif args.command == 'rm-db':
        if args.name not in profiles:
            msg = 'DB profile {0} not found'
            parser.error(msg.format(args.name))
        elif args.name in api_profiles:
            msg = 'Profile {0} is an API profile'
            parser.error(msg.format(args.name))
        else:
            config.pop(args.name)

        with open(config_file, 'wt') as f:
            config.write(f)

        return
    elif args.command == 'rm-api':
        if args.name not in profiles:
            msg = 'API profile {0} not found'
            parser.error(msg.format(args.name))
        elif args.name in db_profiles:
            msg = 'Profile {0} is a DB profile'
            parser.error(msg.format(args.name))
        else:
            config.pop(args.name)

        with open(config_file, 'wt') as f:
            config.write(f)

        return
    elif args.command == 'add-db':
        if args.name == 'DEFAULT':
            parser.error('Profile name may not be "DEFAULT"')
        elif args.name in profiles:
            msg = 'Profile {0} already exists'
            parser.error(msg.format(args.name))
        else:
            config[args.name] = {
                'type': 'database',
                'database_url': args.database_url
            }

        with open(config_file, 'wt') as f:
            config.write(f)

        return
    elif args.command == 'add-api':
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

        return
    else:
        if args.database is not None:
            if args.database in profiles and args.database not in db_profiles:
                msg = 'Profile {0} is not a DB profile'
                parser.error(msg.format(args.database))
            elif args.database not in profiles:
                msg = 'Profile {0} not found'
                parser.error(msg.format(args.database))
            else:
                db_to_use = args.database
        elif len(db_profiles) > 0:
            db_to_use = db_profiles[-1] # order in the file is preserved
        else:
            parser.error('No database profiles configured (use add-db)')

        engine = create_engine(config[db_to_use]['database_url'])

        if args.apis is not None:
            profiles_to_use = args.apis
        else:
            profiles_to_use = api_profiles

        auths = []
        for p in profiles_to_use:
            try:
                assert p in api_profiles

                assert 'consumer_key' in config[p].keys()
                assert 'consumer_secret' in config[p].keys()

                assert not ( \
                    'token' in config[p].keys() and \
                    not 'token_secret' in config[p].keys() \
                )

                assert not ( \
                    'token_secret' in config[p].keys() and \
                    not 'token' in config[p].keys() \
                )
            except AssertionError:
                parser.error('Bad API profile {0}'.format(p))

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
            parser.error('No Twitter credentials provided (use add-api)')

    ##
    ## Commands: main business logic
    ##

    if command == 'initialize':
        if not vars(args).pop('yes'):
            logger.warning("WARNING: This command will drop the Twitter data "
                           "schema and delete all data! If you want to "
                           "proceed, rerun with '-y'.")
        else:
            logger.warning('Recreating schema and dropping existing data')

            md.Base.metadata.drop_all(engine)
            md.Base.metadata.create_all(engine)

        sys.exit(0)

    ## Massage the arguments a bit for passing on to job classes
    command = vars(args).pop('command')

    vars(args).pop('verbose')
    vars(args).pop('database')
    vars(args).pop('apis')
    vars(args).pop('config_file')

    vars(args)['engine'] = engine
    vars(args)['auths'] = auths

    ## Actually run jobs
    if command in ('friends', 'followers'):
        FollowJob(direction=command, **vars(args)).run()
    elif command == 'user_info':
        UserInfoJob(**vars(args)).run()
    else: # command == 'tweets'
        TweetsJob(**vars(args)).run()

if __name__ == '__main__':
    main()

