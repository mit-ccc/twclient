'''
Subcommands which don't interact with the Twitter API
'''

import logging

from .. import job
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
        For all subcommands but list-api and list-db, he name of a profile to
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

    subcommand_to_method = {
        'list-db': 'cli_list_db',
        'list-api': 'cli_list_api',
        'rm-db': 'cli_rm_db',
        'rm-api': 'cli_rm_api',
        'set-db-default': 'cli_set_db_default',
        'add-db': 'cli_add_db',
        'add-api': 'cli_add_api'
    }

    def __init__(self, **kwargs):
        try:
            config_file = kwargs.pop('config_file')
        except KeyError as exc:
            raise ValueError('Must provide config argument') from exc

        full = kwargs.pop('full', None)
        name = kwargs.pop('name', None)
        fle = kwargs.pop('file', None)
        database_url = kwargs.pop('database_url', None)
        consumer_key = kwargs.pop('consumer_key', None)
        consumer_secret = kwargs.pop('consumer_secret', None)
        token = kwargs.pop('token', None)
        token_secret = kwargs.pop('token_secret', None)

        super().__init__(**kwargs)

        self.config_file = os.path.abspath(os.path.expanduser(config_file))
        self.config = self.read_config()

        self.validate_config()

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


    def cli_list_db(self):
        for name in self.config_db_profile_names:
            if self.full:
                print('[' + name + ']')
                for key, value in self.config[name].items():
                    print(key + ' = ' + value)
                print('\n')
            else:
                print(name)

    def cli_list_api(self):
        for name in self.config_api_profile_names:
            if self.full:
                print('[' + name + ']')
                for key, value in self.config[name].items():
                    print(key + ' = ' + value)
                print('\n')
            else:
                print(name)

    def cli_rm_db(self):
        if self.name not in self.config_profile_names:
            msg = 'DB profile {0} not found'
            self.error(msg.format(self.name))
        elif self.name in self.config_api_profile_names:
            self.error(f'Profile {self.name} is an API profile')
        else:
            if self.config.getboolean(self.name, 'is_default'):
                for name in self.config_db_profile_names:
                    if name != self.name:
                        self.config[name]['is_default'] = True
                        break

            self.config.pop(self.name)

        self.write_config()

    def cli_rm_api(self):
        if self.name not in self.config_profile_names:
            msg = 'API profile {0} not found'
            self.error(msg.format(self.name))
        elif self.name in self.config_db_profile_names:
            self.error(f'Profile {self.name} is a DB profile')
        else:
            self.config.pop(self.name)

        self.write_config()

    def cli_set_db_default(self):
        if self.name not in self.config_profile_names:
            msg = 'DB profile {0} not found'
            self.error(msg.format(self.name))
        elif self.name in self.config_api_profile_names:
            self.error(f'Profile {self.name} is an API profile')
        else:
            for name in self.config_db_profile_names:
                self.config[name]['is_default'] = False

            self.config[self.name]['is_default'] = True

        self.write_config()

    def cli_add_db(self):
        if self.name == 'DEFAULT':
            self.error('Profile name may not be "DEFAULT"')
        elif self.name in self.config_profile_names:
            self.error(f'Profile {self.name} already exists')

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
            self.error(f'Profile {self.name} already exists')
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


class InitializeCommand(cmd.DatabaseCommand):
    '''
    The command to (re-)initialize the database schema.

    WARNING! This command drops all data in the database. If not backed up
    elsewhere, it will be lost. The InitializeCommand applies the schema
    defined in the models module against the selected database profile. Any
    existing data is dropped.

    Parameters
    ----------
    yes : bool
        Must be True for anything to be done. The default is False, in which
        case a warning message is emitted on the logger and no changes are
        made. This parameter corresponds to the -y command-line flag.

    Attributes
    ----------
    yes : bool
        The parameter passed to __init__.
    '''

    subcommand_to_method = {
        'initialize': 'cli_initialize'
    }

    def __init__(self, **kwargs):
        yes = kwargs.pop('yes', False)

        # this doesn't actually take a subcommand, just a hack to
        # make it work with the same machinery as the others
        kwargs['subcommand'] = 'initialize'

        super().__init__(**kwargs)

        self.yes = yes

    @property
    def job_args(self):
        return {
            'engine': self.engine
        }

    def cli_initialize(self):
        if not self.yes:
            logger.warning("WARNING: This command will drop the Twitter data "
                           "tables and delete all data! If you want to "
                           "proceed, rerun with -y / --yes.")
        else:
            logger.warning('Recreating schema and dropping existing data')

            job.InitializeJob(**self.job_args).run()


class TagCommand(cmd.DatabaseCommand, cmd.TargetCommand):
    '''
    A command which manages user tags.

    A _TagCommand manages (creates, deletes, or applies to users) the user tags
    that can group users together for easier selection of targets. Subcommands
    are "create", "delete" and "apply".

    Attributes
    ----------
    targets_required
    '''

    subcommand_to_method = {
        'create': 'cli_create',
        'delete': 'cli_delete',
        'apply': 'cli_apply'
    }

    def __init__(self, **kwargs):
        try:
            name = kwargs.pop('name')
        except KeyError as exc:
            raise ValueError('Must provide name argument') from exc

        super().__init__(**kwargs)

        self.name = name

    @property
    def targets_required(self):
        '''
        This attribute from the superclass is a property here. Because targets
        are needed only for the "apply" subcommand, it is True if
        self.subcommand == 'apply' and False otherwise.
        '''

        return self.subcommand == 'apply'

    @property
    def job_args(self):
        args = {
            'tag': self.name,
            'engine': self.engine,
        }

        if self.subcommand == 'apply':
            args['targets'] = self.targets
            args['allow_missing_targets'] = self.allow_missing_targets

        return args

    def cli_create(self):
        job.CreateTagJob(**self.job_args).run()

    def cli_delete(self):
        job.DeleteTagJob(**self.job_args).run()

    def cli_apply(self):
        job.ApplyTagJob(**self.job_args).run()
