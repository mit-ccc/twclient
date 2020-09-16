#!/usr/bin/env python3

# FIXME update logging stuff, esp use __repr__ method on exceptions
# FIXME finish OO rewrite
# FIXME add fetch command, cluster job launching under it

"""
The command-line interface script
"""

import os, sys
import inspect
import logging
import argparse as ap
import collections as cl
import configparser as cp

import tweepy
import sqlalchemy as sa

from . import job
from . import error as err
from . import models as md
from . import target as tg
from . import twitter_api as ta

logger = logging.getLogger(__name__)

class Frontend(object):
    def __init__(self, **kwargs):
        try:
            parser = kwargs.pop('parser')
        except KeyError:
            raise ValueError('Must provide parser argument')

        try:
            config_file = kwargs.pop('config_file')
        except KeyError:
            raise ValueError('Must provide config argument')

        super(Frontend, self).__init__(**kwargs)

        self.parser = parser
        self.config_file = os.path.expanduser(config_file)
        self.config = self.read_config()

    def error(self, msg):
        self.parser.error(msg)

    def read_config(self):
        config = cp.ConfigParser(dict_type=cl.OrderedDict)
        config.read(self.config_file)

        self.validate_config()

        return config

    def write_config(self):
        self.validate_config()

        with open(self.config_file, 'wt') as f:
            self.config.write(f)

    def validate_config(self):
        err_string = 'Malformed configuration file: '

        for s in self.config_profiles:
            if 'type' not in self.config[s].keys():
                msg = 'Section {0} missing type declaration field'
                self.error(err_string + msg.format(s))

            if self.config[s]['type'] not in ('database', 'api'):
                msg = 'Section {0} must have "type" of either "api" or "database"'
                self.error(err_string + msg.format(s))

        for profile in self.config_api_profiles:
            try:
                assert profile in self.config.keys()
                assert self.config[profile]['type'] == 'api'

                assert 'consumer_key' in self.config[profile].keys()
                assert 'consumer_secret' in self.config[profile].keys()

                assert not ( \
                    'token' in self.config[profile].keys() and \
                    not 'token_secret' in self.config[profile].keys() \
                )

                assert not ( \
                    'token_secret' in self.config[profile].keys() and \
                    not 'token' in self.config[profile].keys() \
                )
            except AssertionError:
                self.error(err_string + 'Bad API profile {0}'.format(profile))

        for profile in self.config_db_profiles:
            try:
                assert profile in self.config.keys()
                assert self.config[profile]['type'] == 'database'

                assert 'is_default' in self.config[profile].keys()
                assert 'database_url' in self.config[profile].keys()
            except AssertionError:
                self.error(err_string + 'Bad DB profile {0}'.format(profile))

        try:
            assert sum([
                self.config.getboolean(p, 'is_default')
                for p in self.config_db_profiles
            ]) <= 1
        except AssertionError:
            self.error(err_string + 'Need at most one DB profile marked default')

    def do_cli(self, name):
        func = getattr(self, 'cli_' + name)

        try:
            return func()
        except err.TWClientError as e:
            if logging.getLogger().getEffectiveLevel() == logging.WARNING:
                logger.error(e.message)
            else:
                logger.exception(e.message)

            sys.exit(e.exit_status)

    def run(self):
        self.do_cli(self.args.command)

    ##
    ## Convenience attributes
    ##

    @property
    def config_file(self):
        return os.path.expanduser(self.args.config_file)

    @property
    def config_profiles(self):
        return [ # preserve order
            key
            for key in self.config.keys()
            if key != 'DEFAULT'
        ]

    @property
    def config_db_profiles(self):
        return [
            key
            for key in self.config_profiles
            if self.config[key]['type'] == 'database'
        ]

    @property
    def config_api_profiles(self):
        return [
            key
            for key in self.config_profiles
            if self.config[key]['type'] == 'api'
        ]

    ##
    ## Attributes to pass to jobs
    ##

    @property
    def engine(self):
        if self.args.database is not None:
            if self.args.database in self.config_api_profiles:
                msg = 'Profile {0} is not a DB profile'
                self.error(msg.format(self.args.database))
            elif self.args.database not in self.config_db_profiles:
                msg = 'Profile {0} not found'
                self.error(msg.format(self.args.database))
            else:
                db_to_use = self.args.database
        elif len(self.config_db_profiles) > 0:
            db_to_use = self.config_db_profiles[-1] # order in the file is preserved
        else:
            self.error('No database profiles configured (use add-db)')

        return sa.create_engine(self.config[db_to_use]['database_url'])

    @property
    def api(self):
        if self.args.apis is not None:
            profiles_to_use = self.args.apis
        else:
            profiles_to_use = self.config_api_profiles

        auths = []
        for p in profiles_to_use:
            if 'token' in self.config[p].keys():
                auth = tweepy.OAuthHandler(
                    self.config[p]['consumer_key'],
                    self.config[p]['consumer_secret']
                )

                auth.set_access_token(self.config[p]['token'],
                                      self.config[p]['secret'])
            else:
                auth = tweepy.AppAuthHandler(self.config[p]['consumer_key'],
                                             self.config[p]['consumer_secret'])

            auths += [auth]

        if len(auths) == 0:
            self.error('No Twitter credentials provided (use `config add-api`)')
        else:
            return ta.TwitterApi(auths=auths, abort_on_bad_targets=self.args.abort_on_bad_targets)

    @property
    def targets(self):
        targets = []

        if self.args.user_ids is not None:
            targets += [tg.UserIdTarget(targets=self.args.user_ids)]
        if self.args.screen_names is not None:
            targets += [tg.ScreenNameTarget(targets=self.args.screen_names)]
        if self.args.select_tag is not None:
            targets += [tg.SelectTagTarget(targets=self.args.select_tag)]
        if self.args.twitter_lists is not None:
            targets += [tg.TwitterListTarget(targets=self.args.twitter_lists)]

        if len(targets) == 0:
            self.error('No target users provided')
        else:
            return targets

    ##
    ## Executors for various parts of the CLI
    ##

    def cli_config(self):
        if self.args.subcommand == 'list-db':
            for s in self.config_db_profiles:
                if self.args.full:
                    print('[' + s + ']')
                    for k, v in self.config[s].items():
                        print(k + ' = ' + v)
                    print('\n')
                else:
                    print(s)
        elif self.args.subcommand == 'list-api':
            for s in self.config_api_profiles:
                if self.args.full:
                    print('[' + s + ']')
                    for k, v in self.config[s].items():
                        print(k + ' = ' + v)
                    print('\n')
                else:
                    print(s)
        elif self.args.subcommand == 'rm-db':
            if self.args.name not in self.config_profiles:
                msg = 'DB profile {0} not found'
                self.error(msg.format(self.args.name))
            elif self.args.name in self.config_api_profiles:
                self.error('Profile {0} is an API profile'.format(self.args.name))
            else:
                if self.config.getboolean(self.args.name, 'is_default'):
                    for n in self.config_db_profiles:
                        if n != self.args.name:
                            self.config[n]['is_default'] = True
                            break

                self.config.pop(self.args.name)

            self.write_config()
        elif self.args.subcommand == 'rm-api':
            if self.args.name not in self.config_profiles:
                msg = 'API profile {0} not found'
                self.error(msg.format(self.args.name))
            elif self.args.name in self.config_db_profiles:
                self.error('Profile {0} is a DB profile'.format(self.args.name))
            else:
                self.config.pop(self.args.name)

            self.write_config()
        elif self.args.subcommand == 'add-db':
            if self.args.name == 'DEFAULT':
                self.error('Profile name may not be "DEFAULT"')
            elif self.args.name in self.config_profiles:
                self.error('Profile {0} already exists'.format(self.args.name))

            if self.args.file:
                url = 'sqlite:///' + self.args.file
            else:
                url = self.args.database_url

            self.config[self.args.name] = {
                'type': 'database',
                'is_default': len(self.config_db_profiles) == 0,
                'database_url': url
            }

            self.write_config()
        elif self.args.subcommand == 'add-api':
            if self.args.name == 'DEFAULT':
                self.error('Profile name may not be "DEFAULT"')
            elif self.args.name in self.config_profiles:
                msg = 'Profile {0} already exists'
                self.error(msg.format(self.args.name))
            else:
                self.config[self.args.name] = {
                    'type': 'api',
                    'consumer_key': self.args.consumer_key,
                    'consumer_secret': self.args.consumer_secret
                }

                if self.args.token is not None:
                    self.config[self.args.name]['token'] = self.args.token

                if self.args.token_secret is not None:
                    self.config[self.args.name]['token_secret'] = self.args.token_secret

            self.write_config()
        elif self.args.subcommand == 'set-db-default':
            if self.args.name not in self.config_profiles:
                msg = 'DB profile {0} not found'
                self.error(msg.format(self.args.name))
            elif self.args.name in self.config_api_profiles:
                self.error('Profile {0} is an API profile'.format(self.args.name))
            else:
                for n in self.config_db_profiles:
                    if self.config.getboolean(n, 'is_default'):
                        self.config[n]['is_default'] = False

                    self.config[self.args.name]['is_default'] = True

            self.write_config()
        else:
            self.error('Bad subcommand to cli_config')

    def cli_tag(self):
        if self.args.subcommand == 'create':
            job.CreateTagJob(tag=self.args.name, engine=self.engine).run()
        elif self.args.subcommand == 'delete':
            job.DeleteTagJob(tag=self.args.name, engine=self.engine).run()
        elif self.args.subcommand == 'apply':
            job.ApplyTagJob(tag=self.args.name, targets=self.targets,
                            engine=self.engine).run()
        else:
            self.error('Bad subcommand to cli_tag')

    def cli_initialize(self):
        if not self.args.yes:
            logger.warning("WARNING: This command will drop the Twitter data "
                            "schema and delete all data! If you want to "
                            "proceed, rerun with '-y'.")
        else:
            logger.warning('Recreating schema and dropping existing data')

            md.Base.metadata.drop_all(self.engine)
            md.Base.metadata.create_all(self.engine)

    def cli_fetch(self):
        ## Massage the arguments a bit for passing on to job classes
        args = vars(self.args).copy()

        command = args.pop('command')

        to_drop = ['abort_on_bad_targets', 'verbose', 'database', 'apis',
                    'config_file', 'yes',

                    'select_tag', 'user_ids', 'screen_names', 'twitter_lists']

        for v in to_drop:
            args.pop(v, None)

        args['engine'] = self.engine
        args['api'] = self.twitter_api
        args['targets'] = targets

        ## Actually run jobs
        cls = {
            'hydrate': job.UserInfoJob,
            'friends': job.FriendsJob,
            'followers': job.FollowersJob,
            'tweets': job.TweetsJob
        }[command]

        cls(**args).run()

def make_parser():
    desc = 'Fetch Twitter data and store in a DB schema'
    parser = ap.ArgumentParser(description=desc)

    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='verbosity level (repeat for more)')
    parser.add_argument('-c', '--config-file', default='~/.twclientrc',
                        help='path to config file (default ~/.twclientrc)')

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

    return parser

def cli():
    parser = make_parser()
    args = parser.parse_args()

    verbose = args.pop('verbose')

    if verbose == 0:
        lvl = logging.WARNING
    elif verbose == 1:
        lvl = logging.INFO
    else: # verbose >= 2
        lvl = logging.DEBUG

    fmt = '%(asctime)s : %(module)s : %(levelname)s : %(message)s'
    logging.basicConfig(format=fmt, level=lvl)

    Frontend(parser=parser, **args).run()

if __name__ == '__main__':
    cli()

