'''
Supporting classes for the command-line interface.
'''

import sys
import logging

from abc import ABC, abstractmethod

import tweepy
import sqlalchemy as sa

from ..config import Config
from ..error import BadConfigError, TWClientError
from ..target import (
    UserIdTarget,
    ScreenNameTarget,
    SelectTagTarget,
    TwitterListTarget
)
from ..twitter_api import TwitterApi
from .._utils import TWEEPY_V45

logger = logging.getLogger(__name__)


if TWEEPY_V45:
    _AppAuthHandler = tweepy.OAuth2AppHandler
else:
    _AppAuthHandler = tweepy.AppAuthHandler


class Command(ABC):
    '''
    A command which can be run from the twclient CLI.

    This class encapsulates a command as issued to the twclient command-line
    interface. Each instance of this class represents a subcommand ("fetch",
    "tag", "config", "initialize", etc) given to the CLI, which may take
    further (sub-)subcommands.

    Parameters
    ----------
    parser : argparse.ArgumentParser instance
        The ArgumentParser which parsed the command-line arguments.

    subcommand : str
        The subcommand specifying which operation to perform. (For example,
        "fetch" takes subcommands "tweets", "friends", "followers" and "users.)

    Attributes
    ----------
    parser : argparse.ArgumentParser instance
        The ArgumentParser passed to __init__.

    subcommand : str
        The subcommand passed to __init__.
    '''

    def __init__(self, **kwargs):
        try:
            subcommand = kwargs.pop('subcommand')
        except KeyError as exc:
            raise ValueError('Must provide subcommand argument') from exc

        if subcommand not in self.subcommand_to_job.keys():
            raise ValueError(f'Bad subcommand {subcommand}')

        try:
            parser = kwargs.pop('parser')
        except KeyError as exc:
            raise ValueError('Must provide parser argument') from exc

        config_file = kwargs.pop('config_file', None)

        super().__init__(**kwargs)

        self.subcommand = subcommand
        self.parser = parser

        self.config = Config(config_file=config_file)

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

    def run(self):
        '''
        Run this command.

        This function is the main entrypoint for a Command instance. Any
        error.TWClientError exceptions raised are caught. Such exceptions are
        logged, with an amount of logging output determined by the current log
        level, and then sys.exit is called with whatever exit status the
        exception instance specifies.

        Return
        ------
        The return value of the subcommand's implementing function (see the
        subcommand_to_method dictionary).
        '''

        try:
            cls = self.subcommand_to_job[self.subcommand]
            obj = cls(**self.job_args)

            return obj.run()
        except BadConfigError as exc:
            # We want to print these in a more sane-looking way
            self.error(exc.message)

            sys.exit(exc.exit_status)
        except TWClientError as exc:
            # Don't catch other exceptions: if things we didn't raise reach the
            # toplevel, it's a bug (or, okay, a network issue, Twitter API
            # meltdown, whatever, but nothing to be gained in that case by
            # hiding the whole scary traceback)
            if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
                logger.exception(exc.message)
            else:
                logger.error(exc.message)

            sys.exit(exc.exit_status)

    @property
    @abstractmethod
    def job_args(self):
        '''
        Arguments to be passed through to a subcommand's job class.
        '''

        raise NotImplementedError()

    @property
    @abstractmethod
    def subcommand_to_job(self):
        '''
        A mapping of subcommand name to corresponding job class.

        The subcommand_to_job dictionary maps the names of subcommands as given
        on the command line to the names of the jobs that implement them.
        The job class will be instantiated with kwargs given by the
        ``job_args`` dict and have its ``run()`` method called.
        '''

        raise NotImplementedError()


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

    allow_missing_targets : bool
        Should the Job class continue on encountering targets which should be
        present in the database but aren't (if True) or raise an exception (if
        False, default)?

    Attributes
    ----------
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

        allow_missing_targets = kwargs.pop('allow_missing_targets', False)

        super().__init__(**kwargs)

        targets = []

        if user_ids is not None:
            targets += [UserIdTarget(targets=user_ids)]

        if screen_names is not None:
            targets += [ScreenNameTarget(targets=screen_names)]

        if select_tags is not None:
            targets += [SelectTagTarget(targets=select_tags)]

        if twitter_lists is not None:
            targets += [TwitterListTarget(targets=twitter_lists)]

        if self.targets_required and not targets:
            self.error('No target users provided')

        self.targets = targets
        self.allow_missing_targets = allow_missing_targets


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
            if database in self.config.api_profile_names:
                msg = 'Profile {0} is not a DB profile'
                self.error(msg.format(database))
            elif database not in self.config.db_profile_names:
                msg = 'Profile {0} not found'
                self.error(msg.format(database))
            else:
                db_to_use = database
        elif self.config.db_default_profile_name:
            db_to_use = self.config.db_default_profile_name
        else:
            self.error('No database profile specified and no default profile '
                       'configured (use list-db to see profiles, add-db to '
                       'create a new one, or set-db-default to set an '
                       'existing one as default)')

        self.database = db_to_use
        self.load_batch_size = load_batch_size
        self.database_url = self.config[self.database]['database_url']
        self.engine = sa.create_engine(self.database_url)


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
        allow_api_errors = kwargs.pop('allow_api_errors', False)
        apis = kwargs.pop('apis', None)

        super().__init__(**kwargs)

        self.allow_api_errors = allow_api_errors

        if apis:
            profiles_to_use = apis
        else:
            profiles_to_use = self.config.api_profile_names

        try:
            bad = set(profiles_to_use) - set(self.config.api_profile_names)
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
                auth = _AppAuthHandler(
                    self.config[profile]['consumer_key'],
                    self.config[profile]['consumer_secret']
                )

            auths += [auth]

        if not auths:
            msg = 'No Twitter credentials provided (use `config add-api`)'
            self.error(msg)

        self.api = TwitterApi(auths=auths)
