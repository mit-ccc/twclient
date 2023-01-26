'''
Jobs which modify or display the config file.
'''

import logging

from ._job_base import Job
from .error import BadConfigError
from ._utils import export

logger = logging.getLogger(__name__)


# this is just a stub to placate the linter; the @export decorator adds
# objects to __all__ so that whether an object is included is noted next to it
__all__ = []

@export
class ConfigJob(Job):
    '''
    A job which interacts with the config file.

    Instances of subclasses of ConfigJob do various config-related tasks:
    printing information from the file, adding new DB or API profiles, or
    removing such profiles, among others.

    Parameters
    ----------
    config : instance of Config
        The Config object to work with.

    Attributes
    ----------
    config : instance of Config
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        try:
            config = kwargs.pop('config')
        except KeyError as exc:
            raise ValueError('Must provide config') from exc

        super().__init__(**kwargs)

        self.config = config


@export
class ConfigPrintJob(ConfigJob):
    '''
    A job which prints information from the config file.

    Jobs which are instances of subclasses of this class print various kinds of
    information, such as lists of API credentials or database URLs.

    Parameters
    ----------
    full : bool
        Whether to print profile names only (if False, default), or all
        information (if True).

    Attributes
    ----------
    full : bool
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        full = kwargs.pop('full', None)

        super().__init__(**kwargs)

        self.full = full


@export
class ConfigWriteJob(ConfigJob):
    '''
    A job which modifies the config file.

    Jobs which are instances of subclasses of this class modify the config
    file, for example by adding a new database profile or API credential.

    Parameters
    ----------
    name : str
        The name of the profile to operate on.

    Attributes
    ----------
    name : str
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        name = kwargs.pop('name', None)

        super().__init__(**kwargs)

        self.name = name


@export
class ConfigListDbJob(ConfigPrintJob):
    '''
    List the database profiles given in the config file.
    '''

    def run(self):
        for name in self.config.db_profile_names:
            if self.full:
                print('[' + name + ']')
                for key, value in self.config[name].items():
                    print(key + ' = ' + value)
                print('\n')
            else:
                print(name)


@export
class ConfigListApiJob(ConfigPrintJob):
    '''
    List the API profiles given in the config file.
    '''

    def run(self):
        for name in self.config.api_profile_names:
            if self.full:
                print('[' + name + ']')
                for key, value in self.config[name].items():
                    print(key + ' = ' + value)
                print('\n')
            else:
                print(name)


@export
class ConfigRmDbJob(ConfigWriteJob):
    '''
    Remove a database profile given in the config file.
    '''

    def run(self):
        if self.name not in self.config.profile_names:
            msg = 'DB profile {0} not found'
            raise BadConfigError(message=msg.format(self.name))

        if self.name in self.config.api_profile_names:
            msg = f'Profile {self.name} is an API profile'
            raise BadConfigError(message=msg)

        if self.config.getboolean(self.name, 'is_default'):
            for name in self.config.db_profile_names:
                if name != self.name:
                    self.config[name]['is_default'] = str(True)
                    break

        self.config.pop(self.name)

        self.config.save()


@export
class ConfigRmApiJob(ConfigWriteJob):
    '''
    Remove an API profile given in the config file.
    '''

    def run(self):
        if self.name not in self.config.profile_names:
            msg = 'API profile {0} not found'
            raise BadConfigError(message=msg.format(self.name))

        if self.name in self.config.db_profile_names:
            msg = f'Profile {self.name} is a DB profile'
            raise BadConfigError(message=msg)

        self.config.pop(self.name)

        self.config.save()


@export
class SetDbDefaultJob(ConfigWriteJob):
    '''
    Set a database profile given in the config file as the default DB profile.
    '''

    def run(self):
        if self.name not in self.config.profile_names:
            msg = 'DB profile {0} not found'
            raise BadConfigError(message=msg.format(self.name))

        if self.name in self.config.api_profile_names:
            msg = f'Profile {self.name} is an API profile'
            raise BadConfigError(message=msg)

        for name in self.config.db_profile_names:
            self.config[name]['is_default'] = str(False)

        self.config[self.name]['is_default'] = str(True)

        self.config.save()


@export
class ConfigAddDbJob(ConfigWriteJob):
    '''
    Add a database profile to the config file.

    This job adds a new database to the config file, but does not initialize it
    for later use (that's the ``InitializeJob`` class or ``twitter initialize``
    command). Only databases supported by sqlalchemy can be added, and the
    database must be specified by a sqlalchemy connection URL.

    Parameters
    ----------
    database_url : str
        The sqlalchemy connection URL of the database.

    Attributes
    ----------
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        database_url = kwargs.pop('database_url', None)

        super().__init__(**kwargs)

        self.database_url = database_url

    def run(self):
        if self.name == 'DEFAULT':
            msg = 'Profile name may not be "DEFAULT"'
            raise BadConfigError(message=msg)

        if self.name in self.config.profile_names:
            msg = f'Profile {self.name} already exists'
            raise BadConfigError(message=msg)

        self.config[self.name] = {
            'type': 'database',
            'is_default': len(self.config.db_profile_names) == 0,
            'database_url': self.database_url
        }

        self.config.save()


@export
class ConfigAddApiJob(ConfigWriteJob):
    '''
    Add an API profile to the config file.

    This job adds a set of Twitter credentials to the config file. The
    credential set can involve either a consumer key and secret (OAuth 2) or
    also a token and token secret (OAuth 1a).

    Parameters
    ----------
    consumer_key : str
        The OAuth consumer key.

    consumer_secret : str
        The OAuth consumer secret.

    token : str or None
        The OAuth token.

    token_secret : str or None
        The OAth token secret.

    Attributes
    ----------
    consumer_key : str
        The parameter passed to __init__.

    consumer_secret : str
        The parameter passed to __init__.

    token : str
        The parameter passed to __init__.

    token_secret : str
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        try:
            consumer_key = kwargs.pop('consumer_key')
            consumer_secret = kwargs.pop('consumer_secret')
        except KeyError as exc:
            raise ValueError('Must provide consumer key and secret') from exc

        token = kwargs.pop('token', None)
        token_secret = kwargs.pop('token_secret', None)

        super().__init__(**kwargs)

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.token = token
        self.token_secret = token_secret

    def run(self):
        if self.name == 'DEFAULT':
            msg = 'Profile name may not be "DEFAULT"'
            raise BadConfigError(message=msg)

        if self.name in self.config.profile_names:
            msg = f'Profile {self.name} already exists'
            raise BadConfigError(message=msg)

        self.config[self.name] = {
            'type': 'api',
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret
        }

        if self.token is not None:
            self.config[self.name]['token'] = self.token

        if self.token_secret is not None:
            self.config[self.name]['token_secret'] = self.token_secret

        self.config.save()
