#!/usr/bin/env python3

# FIXME update logging stuff, esp use __repr__ method on exceptions, when should
# we print / call self.error() instead of use logger? or change format?
# basically need consistent output format

"""
The command-line interface script
"""

import os, sys
import logging
import argparse as ap
import collections as cl
import configparser as cp

from abc import ABC, abstractmethod

import tweepy
import sqlalchemy as sa

from . import job
from . import error as err
from . import models as md
from . import target as tg
from . import twitter_api as ta

logger = logging.getLogger(__name__)

class Frontend(ABC):
    def __init__(self, **kwargs):
        try:
            parser = kwargs.pop('parser')
        except KeyError:
            raise ValueError('Must provide parser argument')

        try:
            subcommand = kwargs.pop('subcommand')
        except KeyError:
            raise ValueError('Must provide subcommand argument')

        try:
            config_file = kwargs.pop('config_file')
        except KeyError:
            raise ValueError('Must provide config argument')

        if subcommand not in self.subcommand_to_method.keys():
            raise ValueError('Bad subcommand {0}'.format(subcommand))

        super(Frontend, self).__init__(**kwargs)

        self.parser = parser
        self.subcommand = subcommand

        self.config_file = os.path.abspath(os.path.expanduser(config_file))
        self.config = self.read_config()

    def error(self, msg):
        self.parser.error(msg)

    ##
    ## Interacting with the config file
    ##

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

        for s in self.config_profile_names:
            if 'type' not in self.config[s].keys():
                msg = 'Section {0} missing type declaration field'
                self.error(err_string + msg.format(s))

            if self.config[s]['type'] not in ('database', 'api'):
                msg = 'Section {0} must have "type" of either "api" or "database"'
                self.error(err_string + msg.format(s))

        for profile in self.config_api_profile_names:
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

        for profile in self.config_db_profile_names:
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
                for p in self.config_db_profile_names
            ]) <= 1
        except AssertionError:
            self.error(err_string + 'Need at most one DB profile marked default')

    @property
    def config_profile_names(self):
        return [ # preserve order
            key
            for key in self.config.keys()
            if key != 'DEFAULT'
        ]

    @property
    def config_db_profile_names(self):
        return [
            key
            for key in self.config_profile_names
            if self.config[key]['type'] == 'database'
        ]

    @property
    def config_api_profile_names(self):
        return [
            key
            for key in self.config_profile_names
            if self.config[key]['type'] == 'api'
        ]

    ##
    ## Subclass business logic
    ##

    def do_cli(self, name):
        func = self.subcommand_to_method[name]

        try:
            return func()
        except err.TWClientError as e:
            # Don't catch other exceptions: if things we didn't raise reach the
            # toplevel, it's a bug
            if logging.getLogger().getEffectiveLevel() == logging.WARNING:
                logger.error(e.message)
            else:
                logger.exception(e.message)

            sys.exit(e.exit_status)

    def run(self):
        self.do_cli(self.subcommand)

    @property
    @abstractmethod
    def subcommand_to_method(self):
        raise NotImplementedError()

class DatabaseFrontend(Frontend):
    def __init__(self, **kwargs):
        database = kwargs.pop('database', None)

        super(DatabaseFrontend, self).__init__(**kwargs)

        if database:
            if database in self.config_api_profile_names:
                msg = 'Profile {0} is not a DB profile'
                self.error(msg.format(database))
            elif database not in self.config_db_profile_names:
                msg = 'Profile {0} not found'
                self.error(msg.format(database))
            else:
                db_to_use = database
        elif len(self.config_db_profile_names) > 0:
            # the order they were added is preserved in the file
            db_to_use = self.config_db_profile_names[-1]
        else:
            self.error('No database profiles configured (use add-db)')

        self.database = db_to_use
        self.database_url = self.config[self.database]['database_url']
        self.engine = sa.create_engine(self.database_url)

class TwitterFrontend(Frontend):
    def __init__(self, **kwargs):
        apis = kwargs.get('apis', None)
        abort_on_bad_targets = kwargs.get('abort_on_bad_targets', None)

        super(TwitterFrontend, self).__init__(**kwargs)

        if apis:
            profiles_to_use = apis
        else:
            profiles_to_use = self.config_api_profile_names

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

        self.api = ta.TwitterApi(auths=auths, abort_on_bad_targets=abort_on_bad_targets)

class TargetFrontend(Frontend):
    def __init__(self, **kwargs):
        user_ids = kwargs.pop('user_ids', None)
        screen_names = kwargs.pop('screen_names', None)
        select_tags = kwargs.pop('select_tags', None)
        twitter_lists = kwargs.pop('twitter_lists', None)

        super(TargetFrontend, self).__init__(**kwargs)

        targets = []

        if user_ids is not None:
            targets += [tg.UserIdTarget(targets=user_ids)]

        if screen_names is not None:
            targets += [tg.ScreenNameTarget(targets=screen_names)]

        if select_tags is not None:
            targets += [tg.SelectTagTarget(targets=select_tags)]

        if twitter_lists is not None:
            targets += [tg.TwitterListTarget(targets=twitter_lists)]

        if self.targets_required and len(targets) == 0:
            self.error('No target users provided')

        self.targets = targets

    targets_required = True

class InitializeCommand(DatabaseFrontend):
    def __init__(self, **kwargs):
        yes = kwargs.pop('yes', False)

        # this doesn't actually take a subcommand, just a hack to
        # make it work with the same machinery as the others
        kwargs['subcommand'] = 'initialize'

        super(InitializeFrontend, self).__init__(**kwargs)

        self.yes = yes

    def cli_initialize(self):
        if not self.yes:
            logger.warning("WARNING: This command will drop the Twitter data "
                           "tables and delete all data! If you want to "
                           "proceed, rerun with -y / --yes.")
        else:
            logger.warning('Recreating schema and dropping existing data')

            job.InitializeJob(engine=self.engine).run()

    subcommand_to_method = {
        'initialize': cli_initialize
    }

class FetchCommand(DatabaseFrontend, TargetFrontend, TwitterFrontend):
    def __init__(self, **kwargs):
        load_batch_size = kwargs.get('load_batch_size', 10000)

        # tweet-specific arguments
        since_timestamp = kwargs.get('since_timestamp', None)
        max_tweets = kwargs.get('max_tweets', None)
        old_tweets = kwargs.get('old_tweets', None)

        if subcommand != 'tweets':
            if since_timestamp or max_tweets or old_tweets:
                raise ValueError('since_timestamp, max_tweets and old_tweets '
                                'are only valid with subcommand = "tweets"')

        super(FetchCommand, self).__init__(**kwargs)

        self.load_batch_size = load_batch_size
        self.since_timestamp = since_timestamp
        self.max_tweets = max_tweets
        self.old_tweets = old_tweets

    @property
    def job_args(self):
        args = {
            'engine': self.engine,
            'api': self.api,
            'targets': self.targets,
            'load_batch_size': self.load_batch_size
        }

        if self.subcommand == 'tweets':
            args['since_timestamp'] = self.since_timestamp
            args['max_tweets'] = self.max_tweets
            args['old_tweets'] = self.old_tweets

        return args

    def cli_hydrate(self):
        job.UserInfoJob(**self.job_args).run()

    def cli_friends(self):
        job.FriendsJob(**self.job_args).run()

    def cli_followers(self):
        job.FollowersJob(**self.job_args).run()

    def cli_tweets(self):
        job.TweetsJob(**self.job_args).run()

    subcommand_to_method = {
        'hydrate': cli_hydrate,
        'friends': cli_friends,
        'followers': cli_followers,
        'tweets': cli_tweets
    }

class TagCommand(DatabaseFrontend, TargetFrontend):
    def __init__(self, **kwargs):
        try:
            name = kwargs.pop('name')
        except KeyError:
            raise ValueError('Must provide name argument')

        super(TagCommand, self).__init__(**kwargs)

        self.name = name

    @property
    def targets_required(self):
        return self.subcommand == 'apply'

    def cli_create(self):
        job.CreateTagJob(tag=self.name, engine=self.engine).run()

    def cli_delete(self):
        job.DeleteTagJob(tag=self.name, engine=self.engine).run()

    def cli_apply(self):
        job.ApplyTagJob(tag=self.name, targets=self.targets,
                        engine=self.engine).run()

    subcommand_to_method = {
        'create': cli_create,
        'delete': cli_delete,
        'apply': cli_apply
    }

class ConfigCommand(Frontend):
    def __init__(self, **kwargs):
        full = kwargs.pop('full', None)
        name = kwargs.pop('name', None)
        fle = kwargs.pop('file', None)
        database_url = kwargs.pop('database_url', None)
        consumer_key = kwargs.pop('consumer_key', None)
        consumer_secret = kwargs.pop('consumer_secret', None)
        token = kwargs.pop('token', None)
        token_secret = kwargs.pop('token_secret', None)

        super(ConfigCommand, self).__init__(**kwargs)

        if subcommand not in ('list-db', 'list-api'):
            if name is None:
                msg = 'Must provide name argument for subcommand {0}'
                raise ValueError(msg.format(self.subcommand))

        if subcommand == 'add-api':
            if consumer_key is None or consumer_secret is None:
                msg = 'Must provide consumer_key and consumer_secret ' \
                      'arguments for subcommand {0}'
                raise ValueError(msg.format(self.subcommand))

        if subcommand == 'add-db':
            try:
                assert (fle is None) ^ (database_url is None)
            except AssertionError
                msg = 'Must provide exactly one of file and database_url'
                raise ValueError(msg)

        if fle is not None:
            database_url = 'sqlite:///' + fle

        self.full = full
        self.name = name
        self.database_url = database_url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.token = token
        self.token_secret = token_secret

    def cli_list_db(self):
        for s in self.config_db_profile_names:
            if self.full:
                print('[' + s + ']')
                for k, v in self.config[s].items():
                    print(k + ' = ' + v)
                print('\n')
            else:
                print(s)

    def cli_list_api(self):
        for s in self.config_api_profile_names:
            if self.full:
                print('[' + s + ']')
                for k, v in self.config[s].items():
                    print(k + ' = ' + v)
                print('\n')
            else:
                print(s)

    def cli_rm_db(self):
        if self.name not in self.config_profile_names:
            msg = 'DB profile {0} not found'
            self.error(msg.format(self.name))
        elif self.name in self.config_api_profile_names:
            self.error('Profile {0} is an API profile'.format(self.name))
        else:
            if self.config.getboolean(self.name, 'is_default'):
                for n in self.config_db_profile_names:
                    if n != self.name:
                        self.config[n]['is_default'] = True
                        break

            self.config.pop(self.name)

        self.write_config()

    def cli_rm_api(self):
        if self.name not in self.config_profile_names:
            msg = 'API profile {0} not found'
            self.error(msg.format(self.name))
        elif self.name in self.config_db_profile_names:
            self.error('Profile {0} is a DB profile'.format(self.name))
        else:
            self.config.pop(self.name)

        self.write_config()

    def cli_set_db_default(self):
        if self.name not in self.config_profile_names:
            msg = 'DB profile {0} not found'
            self.error(msg.format(self.name))
        elif self.name in self.config_api_profile_names:
            self.error('Profile {0} is an API profile'.format(self.name))
        else:
            for n in self.config_db_profile_names:
                self.config[n]['is_default'] = False

            self.config[self.name]['is_default'] = True

        self.write_config()

    def cli_add_db(self):
        if self.name == 'DEFAULT':
            self.error('Profile name may not be "DEFAULT"')
        elif self.name in self.config_profile_names:
            self.error('Profile {0} already exists'.format(self.name))

        self.config[self.name] = {
            'type': 'database',
            'is_default': len(self.config_db_profile_names) == 0,
            'database_url': self.database_url
        }

        self.write_config()

    def cli_add_api(self):
        if self.name == 'DEFAULT':
            self.error('Profile name may not be "DEFAULT"')
        elif self.name in self.config_profile_names:
            msg = 'Profile {0} already exists'
            self.error(msg.format(self.name))
        else:
            self.config[self.name] = {
                'type': 'api',
                'consumer_key': self.consumer_key,
                'consumer_secret': self.consumer_secret
            }

            if self.token is not None:
                self.config[self.name]['token'] = self.token

            if self.token_secret is not None:
                self.config[self.name]['token_secret'] = self.token_secret

        self.write_config()

    subcommand_to_method = {
        'list-db': cli_list_db,
        'list-api': cli_list_api,
        'rm-db': cli_rm_db,
        'rm-api': cli_rm_api,
        'set-db-default': cli_set_db_default
        'add-db': cli_add_db,
        'add-api': cli_add_api
    }

def make_parser():
    desc = 'Fetch Twitter data and store in a DB schema'
    parser = ap.ArgumentParser(description=desc)

    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='verbosity level (repeat for more)')
    parser.add_argument('-c', '--config-file', default='~/.twclientrc',
                        help='path to config file (default ~/.twclientrc)')

    def add_target_arguments(p):
        # selecting users to operate on
        p.add_argument('-g', '--select-tags', nargs='+',
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

    config_subparser = sp.add_parser('config', help='Manage configuration')
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
    aap.add_argument('-m', '--consumer-secret', required=True,
                    help='consumer secret')
    aap.add_argument('-t', '--token', help='OAuth token')
    aap.add_argument('-s', '--token-secret', help='OAuth token secret')

    rap = config.add_parser('rm-api', help='remove Twitter API profile')
    rap.add_argument('name', help='name of API profile to remove')

    ## User tagging

    tag_subparser = sp.add_parser('tag', help='Manage user tags')
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

    ## (Re-)initializing the database schema

    inp = sp.add_parser('initialize', help='Initialize the DB schema '
                                        '(WARNING: deletes all data!)')
    inp.add_argument('-d', '--database',
                    help='use this stored DB profile instead of default')
    inp.add_argument('-y', '--yes', action='store_true',
                    help='Must specify this option to initialize')

    ## Fetching Twitter data

    fetch_subparser = sp.add_parser('fetch', help='Fetch Twitter data')
    fetch = fetch_subparser.add_subparsers(dest='subcommand')

    uip = fetch.add_parser('hydrate', help='Get user info / "hydrate" users')
    uip = add_target_arguments(uip)
    uip.add_argument('-d', '--database',
                    help='use this stored DB profile instead of default')
    uip.add_argument('-a', '--api', dest='apis', nargs='+',
                    help='use only these stored API profiles instead ' \
                        'of default')
    uip.add_argument('-b', '--abort-on-bad-targets', action='store_true',
                    help="abort if a requested user doesn't exist")


    frp = fetch.add_parser('friends', help="Get user friends")
    frp = add_target_arguments(frp)
    frp.add_argument('-d', '--database',
                    help='use this stored DB profile instead of default')
    frp.add_argument('-a', '--api', dest='apis', nargs='+',
                    help='use only these stored API profiles instead ' \
                        'of default')
    frp.add_argument('-b', '--abort-on-bad-targets', action='store_true',
                    help="abort if a requested user doesn't exist")

    flp = fetch.add_parser('followers', help="Get user followers")
    flp = add_target_arguments(flp)
    flp.add_argument('-d', '--database',
                    help='use this stored DB profile instead of default')
    flp.add_argument('-a', '--api', dest='apis', nargs='+',
                    help='use only these stored API profiles instead ' \
                        'of default')
    flp.add_argument('-b', '--abort-on-bad-targets', action='store_true',
                    help="abort if a requested user doesn't exist")

    twp = fetch.add_parser('tweets', help="Get user tweets")
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
    twp.add_argument('-z', '--since-timestamp',
                    help='ignore tweets older than this Unix timestamp')
    twp.add_argument('-r', '--max-tweets',
                    help='max number of tweets to collect')

    return parser

def log_setup(verbosity):
    if verbosity == 0:
        lvl = logging.WARNING
    elif verbosity == 1:
        lvl = logging.INFO
    else: # verbosity >= 2
        lvl = logging.DEBUG

    fmt = '%(asctime)s : %(module)s : %(levelname)s : %(message)s'
    logging.basicConfig(format=fmt, level=lvl)

def cli():
    parser = make_parser()
    args = parser.parse_args()

    cmd = args.pop('command')
    verbosity = args.pop('verbose')

    log_setup(verbosity)

    cls = {
        'config': ConfigFrontend,
        'tag': TagFrontend,
        'initialize': InitializeFrontend,
        'fetch': FetchFrontend
    }[cmd]

    cls(parser=parser, **vars(args)).run()

if __name__ == '__main__':
    cli()

