'''
A command to interact with the config file.
'''

import logging

from .._job_config import (
    ConfigListDbJob,
    ConfigListApiJob,
    ConfigRmDbJob,
    ConfigRmApiJob,
    SetDbDefaultJob,
    ConfigAddDbJob,
    ConfigAddApiJob
)
from . import command as cmd

logger = logging.getLogger(__name__)


class ConfigCommand(cmd.Command):
    '''
    A command to manage the config file.

    A ConfigCommand interacts with the config file. It can list or modify the
    contents of the file. Subcommands are roughly divided into two groups: a)
    those which interact with database profiles ("add-db", "rm-db", "list-db",
    "set-db-default") and b) those which interact with API profiles ("add-api",
    "rm-api", "list-api").

    Parameters
    ----------
    full : bool
        For list-api and list-db, whether to print profile names only (if
        False, default), or all information (if True).

    name : str
        For all subcommands but list-api and list-db, the name of a profile to
        operate on.

    fle : str
        For add-db, the path to a file to use as an sqlite database. Cannot be
        specified together with database_url.

    database_url : str
        For add-db, the connection URL of the database. Cannot be specified
        together with fle. (Though an sqlite database may be specified either
        with an "sqlite:///..." url or with the fle argument.)

    consumer_key : str
        For add-api, the OAuth consumer key.

    consumer_secret : str
        For add-api, the OAuth consumer secret.

    token : str
        For add-api, the OAuth token.

    token_secret : str
        For add-api, the OAth token secret.

    Attributes
    ----------
    full : bool
        The parameter passed to __init__.

    name : str
        The parameter passed to __init__.

    database_url : str
        The final database url. If database_url was passed to __init__, that
        value is recorded here; if fle was passed, the value is "sqlite:///" +
        fle.

    consumer_key : str
        The parameter passed to __init__.

    consumer_secret : str
        The parameter passed to __init__.

    token : str
        The parameter passed to __init__.

    token_secret : str
        The parameter passed to __init__.
    '''

    subcommand_to_job = {
        'list-db': ConfigListDbJob,
        'list-api': ConfigListApiJob,
        'rm-db': ConfigRmDbJob,
        'rm-api': ConfigRmApiJob,
        'set-db-default': SetDbDefaultJob,
        'add-db': ConfigAddDbJob,
        'add-api': ConfigAddApiJob
    }

    def __init__(self, **kwargs):
        full = kwargs.pop('full', None)
        name = kwargs.pop('name', None)
        fle = kwargs.pop('file', None)
        database_url = kwargs.pop('database_url', None)
        consumer_key = kwargs.pop('consumer_key', None)
        consumer_secret = kwargs.pop('consumer_secret', None)
        token = kwargs.pop('token', None)
        token_secret = kwargs.pop('token_secret', None)

        super().__init__(**kwargs)

        if self.subcommand not in ('list-db', 'list-api'):
            if name is None:
                msg = 'Must provide name argument for subcommand {0}'
                raise ValueError(msg.format(self.subcommand))

        if self.subcommand == 'add-api':
            if consumer_key is None or consumer_secret is None:
                msg = 'Must provide consumer_key and consumer_secret ' \
                      'arguments for subcommand {0}'
                raise ValueError(msg.format(self.subcommand))

        if self.subcommand == 'add-db':
            try:
                assert (fle is None) ^ (database_url is None)
            except AssertionError as exc:
                msg = 'Must provide exactly one of file and database_url'
                raise ValueError(msg) from exc

        if fle is not None:
            database_url = 'sqlite:///' + fle

        self.full = full
        self.name = name
        self.database_url = database_url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.token = token
        self.token_secret = token_secret

    @property
    def job_args(self):
        ret = {
            'config': self.config
        }

        if self.subcommand in ('list-db', 'list-api'):
            ret['full'] = self.full

        if self.subcommand not in ('list-db', 'list-api'):
            ret['name'] = self.name

        if self.subcommand == 'add-db':
            ret['database_url'] = self.database_url

        if self.subcommand == 'add-api':
            ret['consumer_key'] = self.consumer_key
            ret['consumer_secret'] = self.consumer_secret
            ret['token'] = self.token
            ret['token_secret'] = self.token_secret

        return ret
