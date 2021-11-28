'''
Supporting classes for the command-line interface.
'''

import os
import sys
import logging
import collections as cl
import configparser as cp

from abc import ABC, abstractmethod

import tweepy
import sqlalchemy as sa

from .. import job
from .. import error as err
from .. import target as tg
from .. import twitter_api as ta

logger = logging.getLogger(__name__)


class Command(ABC):
    '''
    A command which can be run from the twclient CLI.

    This class encapsulates a command as issued to the twclient command-line
    interface. Each instance of this class represents a subcommand ("fetch",
    "tag", "config" or "initialize") given to the CLI, and all but "initialize"
    take further (sub-)subcommands.

    Parameters
    ----------
    parser : argparse.ArgumentParser instance
        The ArgumentParser which parsed the command-line arguments.
    subcommand : str
        The subcommand specifying which operation to perform. (For example,
        "fetch" takes subcommands "tweets", "friends", "followers" and "users.)
    config_file : str
        The (possibly relative) path to the config file. Tilde expansion will
        be performed.

    Attributes
    ----------
    parser : argparse.ArgumentParser instance
        The ArgumentParser passed to __init__.

    subcommand : str
        The subcommand passed to __init__.

    config_file : str
        The absolute path to the config file, after tilde expansion.
    '''

    def __init__(self, **kwargs):
        try:
            parser = kwargs.pop('parser')
        except KeyError as exc:
            raise ValueError('Must provide parser argument') from exc

        try:
            subcommand = kwargs.pop('subcommand')
        except KeyError as exc:
            raise ValueError('Must provide subcommand argument') from exc

        try:
            config_file = kwargs.pop('config_file')
        except KeyError as exc:
            raise ValueError('Must provide config argument') from exc

        if subcommand not in self.subcommand_to_method.keys():
            raise ValueError(f'Bad subcommand {subcommand}')

        super().__init__(**kwargs)

        self.parser = parser
        self.subcommand = subcommand

        self.config_file = os.path.abspath(os.path.expanduser(config_file))
        self.config = self.read_config()

        self.validate_config()

    # NOTE using this for some errors and logger.____ for others isn't a bug
    # or problem per se, but it does lead to inconsistent output formatting
    def error(self, msg):
        '''
        Log an error encountered by this command and exit.

        This function logs a message about an error encountered by the _Command
        instance and exits. Currently it calls the error() method on the
        program's argparse.ArgumentParser object, but this may change.

        Parameters
        ----------
        msg : str
            A message describing the error.

        Returns
        -------
        None
        '''

        self.parser.error(msg)

    #
    # Interacting with the config file
    #

    def read_config(self):
        '''
        Read and return the config file.

        This function reads the config file specified to __init__ and returns
        it as a ConfigParser object.

        Returns
        -------
        None
        '''

        config = cp.ConfigParser(dict_type=cl.OrderedDict)
        config.read(self.config_file)

        return config

    def write_config(self):
        '''
        Write the current state of the config back to the config file.

        This function writes the current state of this _Command's config out to
        the path given for the config file. The config is validated before
        being written.

        Returns
        -------
        None
        '''

        self.validate_config()

        with open(self.config_file, 'wt', encoding='utf-8') as fobj:
            self.config.write(fobj)

    def validate_config(self):
        '''
        Validate the current state of this _Command's config.

        This function performs several checks of the validity of this
        _Command's config, and calls the error() method if any problem is
        detected.

        Returns
        -------
        None
        '''

        err_string = 'Malformed configuration file: '

        for name in self.config_profile_names:
            if 'type' not in self.config[name].keys():
                msg = 'Section {0} missing type declaration field'
                self.error(err_string + msg.format(name))

            if self.config[name]['type'] not in ('database', 'api'):
                msg = 'Section {0} must have "type" of either ' \
                      '"api" or "database"'
                self.error(err_string + msg.format(name))

        for profile in self.config_api_profile_names:
            try:
                assert profile in self.config.keys()
                assert self.config[profile]['type'] == 'api'

                assert 'consumer_key' in self.config[profile].keys()
                assert 'consumer_secret' in self.config[profile].keys()

                assert not (
                    'token' in self.config[profile].keys() and
                    'token_secret' not in self.config[profile].keys()
                )

                assert not (
                    'token_secret' in self.config[profile].keys() and
                    'token' not in self.config[profile].keys()
                )
            except AssertionError:
                self.error(err_string + f'Bad API profile {profile}')

        for profile in self.config_db_profile_names:
            try:
                assert profile in self.config.keys()
                assert self.config[profile]['type'] == 'database'

                assert 'is_default' in self.config[profile].keys()
                assert 'database_url' in self.config[profile].keys()
            except AssertionError:
                self.error(err_string + f'Bad DB profile {profile}')

        try:
            assert sum([
                self.config.getboolean(p, 'is_default')
                for p in self.config_db_profile_names
            ]) <= 1
        except AssertionError:
            msg = err_string + 'Need at most one DB profile marked default'
            self.error(msg)

    @property
    def config_profile_names(self):
        '''
        The names of all database and API profiles in the config.

        The config file consists of "profiles" for different databases and
        Twitter API credential sets. Each has a type (database or API);
        database profiles have URLs to pass to sqlalchemy and API profiles
        have OAuth keys, tokens and secrets. One of the database profiles is
        marked as the default, to use if no database profile is given on the
        commad line.
        '''

        return [  # preserve order
            key
            for key in self.config.keys()
            if key != 'DEFAULT'
        ]

    @property
    def config_db_profile_names(self):
        '''
        The names of all database profiles in the config.
        '''

        return [
            key
            for key in self.config_profile_names
            if self.config[key]['type'] == 'database'
        ]

    @property
    def config_api_profile_names(self):
        '''
        The names of all API profiles in the config.
        '''

        return [
            key
            for key in self.config_profile_names
            if self.config[key]['type'] == 'api'
        ]

    #
    # Subclass business logic
    #

    def do_cli(self, name):
        '''
        Execute a subcommand by name.

        This method takes the name of a subcommand, looks up the corresponding
        method (see the subcommand_to_method dictionary) and executes it. The
        subcommand method is called with no arguments, and any
        error.TWClientError exceptions raised are caught. Such exceptions are
        logged, with an amount of logging output determined by the current log
        level, and then sys.exit is called with whatever exit status the
        exception instance specifies.

        Return
        ------
        The return value of the subcommand's implementing function (see the
        subcommand_to_method dictionary).
        '''

        func = getattr(self, self.subcommand_to_method[name])

        try:
            return func()
        except err.TWClientError as exc:
            # Don't catch other exceptions: if things we didn't raise reach the
            # toplevel, it's a bug (or, okay, a network issue, Twitter API
            # meltdown, whatever, but nothing to be gained in that case by
            # hiding the whole scary traceback)
            if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
                logger.exception(exc.message)
            else:
                logger.error(exc.message)

            sys.exit(exc.exit_status)

    def run(self):
        '''
        Run this command.

        This function is the main entrypoint for a Command instance. It
        dispatches the name of the subcommand to do_cli() for further
        processing.

        Return
        ------
        The return value of the subcommand's implementing function (see the
        subcommand_to_method dictionary).
        '''

        return self.do_cli(self.subcommand)

    @property
    @abstractmethod
    def subcommand_to_method(self):
        '''
        A mapping of subcommand name to implementing method.

        The subcommand_to_method dictionary maps the names of subcommands as
        given on the command line to the names of methods called to implement
        them. The method name will be called with no arguments (see the
        do_cli() method).
        '''

        raise NotImplementedError()


class DatabaseCommand(Command):
    '''
    A command which uses database resources.

    This class represents commands which require access to the database,
    whether to store newly fetched information from Twitter or to modify
    information already there.

    Parameters
    ----------
    database : str, or None
        The name of a database profile to use. If None, use the config file's
        current default.

    load_batch_size : int, or None
        Load data to the database in batches of this size. The default is None,
        which means load all data in one batch and is fastest. Other values can
        minimize memory usage for large amounts of data at the cost of slower
        loading.

    Attributes
    ----------
    database : str
        The name of the database profile in use, including the config file
        default if none is given to __init__.

    load_batch_size : int, or None
        The parameter passed to __init__.

    database_url : str
        The connection URL for the requested database profile, read from the
        config file. (This URL should be acceptable to sqlalchemy's
        create_engine function.)

    engine : sqlalchemy.engine.Engine instance
        The sqlalchemy engine for the selected database profile.
    '''

    def __init__(self, **kwargs):
        database = kwargs.pop('database', None)
        load_batch_size = kwargs.pop('load_batch_size', None)

        super().__init__(**kwargs)

        if database:
            if database in self.config_api_profile_names:
                msg = 'Profile {0} is not a DB profile'
                self.error(msg.format(database))
            elif database not in self.config_db_profile_names:
                msg = 'Profile {0} not found'
                self.error(msg.format(database))
            else:
                db_to_use = database
        elif self.config_db_profile_names:
            # the order they were added is preserved in the file
            db_to_use = self.config_db_profile_names[-1]
        else:
            self.error('No database profiles configured (use add-db)')

        self.database = db_to_use
        self.load_batch_size = load_batch_size
        self.database_url = self.config[self.database]['database_url']
        self.engine = sa.create_engine(self.database_url)


class TargetCommand(Command):
    '''
    A command which takes targets.

    This class represents commands which operate on users as specified by
    various kinds of targets. These commands include ones which fetch Twitter
    data as well as the `tag apply` command that tags already loaded users.

    Parameters
    ----------
    user_ids : list of int
        Twitter user IDs to operate on.

    screen_names : list of str
        Twitter screen names to operate on.

    select_tags : list of str
        User tags stored in the database, specifying users to operate on.

    twitter_lists : list of str or int
        The Twitter lists whose member users to operate on, whether list IDs or
        in the form owning_user/slug, like "cspan/members-of-congress". If a
        passed element is str, it will be identified as list-ID or owner/slug
        format by the presence of a slash.

    randomize : bool
        Shoul the targets be processd in a randomized order? Passed through to
        the Target classes.

    allow_missing_targets : bool
        Should the Job class continue on encountering targets which should be
        present in the database but aren't (if True) or raise an exception (if
        False, default)?

    Attributes
    ----------
    randomize : bool
        The parameter passed to __init__.

    allow_missing_targets : bool
        The parameter passed to __init__.

    targets : list of target.Target instances
        The targets constructed from the user IDs, screen names, etc, passed to
        __init__.

    targets_required : bool
        This class attribute specifies whether the subclass requires target
        users (if True) or if they are optional (if False). If True, an error
        will be raised if user_ids, screen_names, select_tags and twitter_lists
        are all None. The default set on this class, which subclasses may
        override, is True.
    '''

    targets_required = True

    def __init__(self, **kwargs):
        user_ids = kwargs.pop('user_ids', None)
        screen_names = kwargs.pop('screen_names', None)
        select_tags = kwargs.pop('select_tags', None)
        twitter_lists = kwargs.pop('twitter_lists', None)

        randomize = kwargs.pop('randomize', False)
        allow_missing_targets = kwargs.pop('allow_missing_targets', False)

        super().__init__(**kwargs)

        targets = []

        if user_ids is not None:
            targets += [
                tg.UserIdTarget(targets=user_ids, randomize=randomize)
            ]

        if screen_names is not None:
            targets += [
                tg.ScreenNameTarget(targets=screen_names, randomize=randomize)
            ]

        if select_tags is not None:
            targets += [
                tg.SelectTagTarget(targets=select_tags, randomize=randomize)
            ]

        if twitter_lists is not None:
            targets += [
                tg.TwitterListTarget(targets=twitter_lists,
                                     randomize=randomize)
            ]

        if self.targets_required and not targets:
            self.error('No target users provided')

        self.targets = targets
        self.randomize = randomize
        self.allow_missing_targets = allow_missing_targets


class ApiCommand(Command):
    '''
    A command which uses Twitter API resources.

    This class represents commands which require access to the Twitter API to
    fetch new data.

    Parameters
    ----------
    apis : list of str, or None
        The names of API profiles in the config file to use. If None, all
        available API profiles are used.

    allow_api_errors : bool
        Should this command continue if it encounters a Twitter API error (if
        True) or abort (if False, default)?

    Attributes
    ----------
    api : twitter_api.TwitterApi instance
        The TwitterApi instance constructed from the selected API credentials.

    allow_api_errors : bool
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        apis = kwargs.pop('apis', None)
        allow_api_errors = kwargs.pop('allow_api_errors', False)

        super().__init__(**kwargs)

        if apis:
            profiles_to_use = apis
        else:
            profiles_to_use = self.config_api_profile_names

        try:
            bad = set(profiles_to_use) - set(self.config_api_profile_names)
            assert len(bad) == 0
        except AssertionError as exc:
            raise ValueError(f'Bad API profile names: {bad}') from exc

        auths = []
        for profile in profiles_to_use:
            if 'token' in self.config[profile].keys():
                auth = tweepy.OAuthHandler(
                    self.config[profile]['consumer_key'],
                    self.config[profile]['consumer_secret']
                )

                auth.set_access_token(self.config[profile]['token'],
                                      self.config[profile]['secret'])
            else:
                auth = tweepy.AppAuthHandler(
                    self.config[profile]['consumer_key'],
                    self.config[profile]['consumer_secret']
                )

            auths += [auth]

        if not auths:
            msg = 'No Twitter credentials provided (use `config add-api`)'
            self.error(msg)

        self.allow_api_errors = allow_api_errors
        self.api = ta.TwitterApi(auths=auths)
