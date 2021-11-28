'''
Objects representing twclient configuration.
'''

import logging

import os
import collections as cl
import configparser as cp

from . import error as err

logger = logging.getLogger(__name__)

class Config:
    '''
    A configuration including database and API profiles.

    This class represents the config file. It can list or modify the
    contents of the file, and may work with either the API or DB profiles
    listed there.

    Parameters
    ----------
    config_file : str
        The path to the config file. This value will undergo tilde expansion
        and be converted to an absolute path before its contents are loaded.

    Attributes
    ----------
    name : str
        The tilde-expanded, absolute-path version of the parameter passed to
        __init__.
    '''

    def __init__(self, **kwargs):
        # NOTE we want it provided *and* not None, not just the usual
        # try-pop-catch-KeyError routine
        config_file = kwargs.pop('config_file', None)
        if config_file is None:
            raise ValueError('Must provide config_file argument')

        super().__init__(**kwargs)

        self.raw_config_file = config_file
        self.config_file = os.path.abspath(os.path.expanduser(config_file))

        self.config = self.read_config()
        self.validate()

    @property
    def profile_names(self):
        '''
        The names of all database and API profiles in the config.

        The config file consists of "profiles" for different databases and
        Twitter API credential sets. Each has a type (database or API);
        database profiles have URLs to pass to sqlalchemy and API profiles
        have OAuth keys, tokens and secrets. One of the database profiles is
        marked as the default, to use if no database profile is given on the
        command line.
        '''

        return [  # preserve order
            key
            for key in self.config.keys()
            if key != 'DEFAULT'
        ]

    @property
    def db_profile_names(self):
        '''
        The names of all database profiles in the config.
        '''

        return [
            key
            for key in self.profile_names
            if self.config[key]['type'] == 'database'
        ]

    @property
    def api_profile_names(self):
        '''
        The names of all API profiles in the config.
        '''

        return [
            key
            for key in self.profile_names
            if self.config[key]['type'] == 'api'
        ]

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
        Write the current state of the Config back to the config file.

        This method writes the current state of this Config out to the path
        given for the config file. The config is validated before being
        written.

        Returns
        -------
        None
        '''

        self.validate()

        with open(self.config_file, 'wt', encoding='utf-8') as fobj:
            self.config.write(fobj)

    def validate(self):
        '''
        Validate the current state of this Config.

        This method performs several checks of the validity of this Config, and
        raises ``BadConfigError`` if any problem is detected.

        Returns
        -------
        None
        '''

        err_string = 'Malformed configuration file: '

        for name in self.profile_names:
            if 'type' not in self.config[name].keys():
                msg = 'Section {0} missing type declaration field'
                msg = err_string + msg.format(name)

                raise err.BadConfigError(message=msg)

            if self.config[name]['type'] not in ('database', 'api'):
                msg = 'Section {0} must have "type" of either ' \
                      '"api" or "database"'
                msg = err_string + msg.format(name)

                raise err.BadConfigError(message=msg)

        for profile in self.api_profile_names:
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
            except AssertionError as exc:
                msg = err_string + f'Bad API profile {profile}'
                raise err.BadConfigError(message=msg) from exc

        for profile in self.db_profile_names:
            try:
                assert profile in self.config.keys()
                assert self.config[profile]['type'] == 'database'

                assert 'is_default' in self.config[profile].keys()
                assert 'database_url' in self.config[profile].keys()
            except AssertionError as exc:
                msg = err_string + f'Bad DB profile {profile}'
                raise err.BadConfigError(message=msg) from exc

        try:
            assert sum([
                self.config.getboolean(p, 'is_default')
                for p in self.db_profile_names
            ]) <= 1
        except AssertionError as exc:
            msg = err_string + 'Need at most one DB profile marked default'
            raise err.BadConfigError(message=msg) from exc
