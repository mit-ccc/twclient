'''
Job classes which actually implement command logic.
'''

import logging
import itertools as it

from abc import ABC, abstractmethod

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from ._version import __version__
from .error import BadSchemaError, BadTargetError
from .models import SchemaVersion
from ._utils import export

logger = logging.getLogger(__name__)


# this is just a stub to placate the linter; the @export decorator adds
# objects to __all__ so that whether an object is included is noted next to it
__all__ = []

@export
class Job(ABC):
    '''
    A job to be run against the database and possibly also the Twitter API.
    '''

    # This method is the main entrypoint for the Job class. Subclasses are
    # expected to override it with their business logic.
    @abstractmethod
    def run(self):
        '''
        Run the job.
        '''

        raise NotImplementedError()


@export
class DatabaseJob(Job):
    '''
    A job to be run against the database.

    This class represents a job to be run against the database. Subclasses may
    or may not also support access to the Twitter API.

    Parameters
    ----------
    engine : sqlalchemy.engine.Engine instance
        The sqlalchemy engine representing the database to connect to.

    Attributes
    ----------
    engine : sqlalchemy.engine.Engine instance
        The parameter passed to __init__.

    session : sqlalchemy.orm.session.Session instance
        The actual database session to use.
    '''

    def __init__(self, **kwargs):
        try:
            engine = kwargs.pop('engine')
        except KeyError as exc:
            raise ValueError("engine instance is required") from exc

        super().__init__(**kwargs)

        self.engine = engine

        self._sessionfactory = sessionmaker()
        self._sessionfactory.configure(bind=self.engine)

        self.session = self._sessionfactory()

        self._schema_verified = False

    def ensure_schema_version(self):
        '''
        Ensure that the database schema is a usable version.

        This method checks that the schema present in the database referred to
        by self.engine is a version the Job class knows how to work with. If
        the schema is an unsupported version or is missing / corrupt, an
        instance of error.BadSchemaError will be raised.

        Returns
        -------
        None
        '''

        if self._schema_verified:
            return

        try:
            schema_version = self.session.query(SchemaVersion).all()
        except sa.exc.ProgrammingError as exc:
            msg = 'Bad or missing schema version tag in database (have you ' \
                  'initialized it?)'
            raise BadSchemaError(message=msg) from exc

        if len(schema_version) != 1:
            msg = 'Bad or missing schema version tag in database'
            raise BadSchemaError(message=msg)

        db_version = schema_version[0].version

        if db_version > __version__:
            msg = 'Package version {0} cannot use future schema version {1}'
            msg = msg.format(__version__, db_version)
            raise BadSchemaError(message=msg)

        if db_version < __version__:  # likely to change in future versions
            msg = 'Package version {0} cannot migrate old schema version ' \
                  '{1}; consider downgrading the package version'
            msg = msg.format(__version__, db_version)
            raise BadSchemaError(message=msg)

        self._schema_verified = True

    def get_or_create(self, model, **kwargs):
        '''
        Get a persistent object or create a pending one.

        Given a model and a set of kwargs, interpretable as the values of the
        model's attributes, which together should identify one row in the
        database, query for it and a) return a persistent object if the
        row exists, or otherwise b) create and return a pending object with the
        appropriate attribute values.

        Parameters
        ----------
        model : instance of models.Base
            A sqlalchemy model object.

        **kwargs
            Keyword arguments specifying the values of the model's attributes.

        Returns
        -------
        instance of models.Base
            The persistent or pending object.
        '''

        instance = self.session.query(model).filter_by(**kwargs).one_or_none()

        if instance:
            return instance

        instance = model(**kwargs)
        self.session.add(instance)

        return instance


@export
class TargetJob(DatabaseJob):
    '''
    A job which requires targets.

    A TargetJob is a job which requires a set of target.Target instances to
    specify users. An instance of this class must specify its resolve mode for
    the Target classes, and has defaut logic to resolve them and expose their
    users.

    Parameters
    ----------
    targets : list of target.Target
        The list of targets for the job.

    allow_missing_targets : bool
        If resolving the targets indicates that some targets should be in the
        database but are not (i.e., one of the Target instances in self.targets
        has a non-empty missing_targets attribute), should we raise
        error.BadTargetError (if False, default) or continue and ignore the
        missing targets (if True)?

    Attributes
    ----------
    targets : list of target.Target
        The parameter passed to __init__.

    allow_missing_targets : bool
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        targets = kwargs.pop('targets', [])
        allow_missing_targets = kwargs.pop('allow_missing_targets', False)

        super().__init__(**kwargs)

        self.targets = targets
        self.allow_missing_targets = allow_missing_targets

        self.ensure_schema_version()

    @property
    @abstractmethod
    def resolve_mode(self):
        '''
        The resolve mode attribute to specify behavior of Target instances.

        This attribute is consumed by the Target instances in self.targets.
        Acceptable values include 'fetch', 'skip', 'hydrate'. See the
        documentation for target.Target for more information.
        '''

        raise NotImplementedError()

    @property
    def resolved(self):
        '''
        Have all targets been resolved to users?

        This attribute is false on instantiation, and is normally set to True
        by calling resolve_targets().
        '''

        return all(t.resolved for t in self.targets)

    def _combine_sub_attrs(self, attr):
        if not self.resolved:
            raise AttributeError('Must call resolve_targets() first')

        return list(it.chain(*[getattr(t, attr) for t in self.targets]))

    @property
    def users(self):
        '''
        The combined set of users referred to by all targets.

        This is the union of all the users referred to by the Target instances
        in self.targets. If the targets have not been resolved, accessing this
        attribute will raise AttributeError.
        '''

        return self._combine_sub_attrs('users')

    @property
    def bad_targets(self):
        '''
        The combined set of bad raw targets referred to by all targets.

        This is the union of all the bad raw targets in the Target instances in
        self.targets. If the targets have not been resolved, accessing this
        attribute will raise AttributeError. See the documentation for
        target.Target for details of what a target and raw target are and its
        bad_targets attribute for what it means for a raw target to be bad.
        '''

        return self._combine_sub_attrs('bad_targets')

    @property
    def missing_targets(self):
        '''
        The combined set of missing raw targets referred to by all targets.

        This is the union of all the missing raw targets in the Target
        instances in self.targets. If the targets have not been resolved,
        accessing this attribute will raise AttributeError. See the
        documentation for target.Target for details of what a target and raw
        target are and its missing_targets attribute for what it means for a
        raw target to be missing.
        '''

        return self._combine_sub_attrs('missing_targets')

    @property
    def good_targets(self):
        '''
        The combined set of good raw targets referred to by all targets.

        This is the union of all the good raw targets in the Target instances
        in self.targets. If the targets have not been resolved, accessing this
        attribute will raise AttributeError. See the documentation for
        target.Target for details of what a target and raw target are and its
        good_targets attribute for what it means for a raw target to be good.
        '''

        return self._combine_sub_attrs('good_targets')

    def resolve_targets(self):
        '''
        Resolve all of the targets in self.targets to users.

        This method resolves all of the targets in self.targets to users (and
        bad/missing raw targets, if applicable) and validates them using
        whatever logic the subclass has defined for validate_targets().
        '''

        for target in self.targets:
            target.resolve(context=self)

        self.validate_targets()

    def validate_targets(self):
        '''
        Validate the targets in self.targets.

        This method is a hook called by resolve_targets to ensure that the
        targets in self.targets have resolved into a sane configuration. If any
        error is detected, error.BadTargetError should be raised. The default
        implementation here checks whether there are missing targets (i.e.,
        targets which should have been but were not found in the database), and
        raises error.BadTargetError unless self.allow_missing_targets evaluates
        to True. Subclasses may override with other configurations.
        '''

        if self.resolve_mode == 'skip' and self.missing_targets:
            msg = 'Target(s) not in database: {0}'
            msg = msg.format(', '.join(self.missing_targets))

            if self.allow_missing_targets:
                logger.warning(msg)
            else:
                raise BadTargetError(
                    message=msg,
                    targets=self.missing_targets
                )


@export
class ApiJob(Job):
    '''
    A job requiring acess to the Twitter API.

    This class represents a job which interacts with the Twitter API. It
    configures API access, and defers other functionality to subclasses.

    Parameters
    ----------
    api : instance of twitter_api.TwitterApi
        The TwitterApi instance to use for API access.

    allow_api_errors : bool
        If the Twitter API returns an error, should we abort (if False,
        default), or ignore and continue (if True)?

    Attributes
    ----------
    api : instance of twitter_api.TwitterApi
        The parameter passed to __init__.

    allow_api_errors : bool
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        try:
            api = kwargs.pop('api')
        except KeyError as exc:
            raise ValueError('Must provide api object') from exc

        allow_api_errors = kwargs.pop('allow_api_errors', False)

        super().__init__(**kwargs)

        self.api = api
        self.allow_api_errors = allow_api_errors
