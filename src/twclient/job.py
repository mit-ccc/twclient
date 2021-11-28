'''
Job classes which actually implement command logic.
'''

import json
import logging
import warnings
import itertools as it

from abc import ABC, abstractmethod

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from . import __version__
from . import error as err
from . import _utils as ut
from . import models as md

logger = logging.getLogger(__name__)

# This isn't a great way to handle these warnings, but sqlalchemy is so dynamic
# that most attribute accesses aren't resolved until runtime
# pylint: disable=no-member

#
# Job classes
# These encapsulate different types of loading jobs, including
# the details of interacting with the database and Twitter API
#


class Job(ABC):  # pylint: disable=too-few-public-methods
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
            schema_version = self.session.query(md.SchemaVersion).all()
        except sa.exc.ProgrammingError as exc:
            msg = 'Bad or missing schema version tag in database (have you ' \
                  'initialized it?)'
            raise err.BadSchemaError(message=msg) from exc

        if len(schema_version) != 1:
            msg = 'Bad or missing schema version tag in database'
            raise err.BadSchemaError(message=msg)

        db_version = schema_version[0].version

        if db_version > __version__:
            msg = 'Package version {0} cannot use future schema version {1}'
            msg = msg.format(__version__, db_version)
            raise err.BadSchemaError(message=msg)

        if db_version < __version__:  # likely to change in future versions
            msg = 'Package version {0} cannot migrate old schema version ' \
                  '{1}; consider downgrading the package version'
            msg = msg.format(__version__, db_version)
            raise err.BadSchemaError(message=msg)

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


class TagJob(DatabaseJob):
    '''
    A job which uses user tags.

    A TagJob is a class which requires a user tag. It ensures that the database
    schema version is correct, and leaves other logic for subclasses.

    Parameters
    ----------
    tag : str
        The name of a user tag.

    Attributes
    ----------
    tag : str
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        try:
            tag = kwargs.pop('tag')
        except KeyError as exc:
            raise ValueError('Must provide tag argument') from exc

        super().__init__(**kwargs)

        self.tag = tag

        self.ensure_schema_version()


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
        try:
            targets = kwargs.pop('targets')
        except KeyError as exc:
            raise ValueError('Must provide list of targets') from exc

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
                raise err.BadTargetError(
                    message=msg,
                    targets=self.missing_targets
                )


class ApiJob(Job):  # pylint: disable=too-few-public-methods
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


class FetchJob(ApiJob, TargetJob):
    '''
    A job fetching data from the Twitter API.

    This class represents a job which fetches data from the Twitter API. It
    configures API access and user validation logic, and defers other
    functionality to subclasses.

    Parameters
    ----------
    load_batch_size : int
        Load new rows to the database in batches of this size. The default is
        None, which loads all data retrieved in one batch. Lower values
        minimize memory usage at the cost of slower loading speeds, while
        higher values do the reverse. Target instances in self.targets do not
        consider this value--it applies only to other rows loaded by the FetchJob
        instance--because there are generally not enough targets to consume a
        significant amount of memory. Followers and friends lists in particular
        can be large enough to cause out-of-memory conditions; setting
        ``load_batch_size`` to an appropriate value (e.g., 5000) can address
        this problem.

    Attributes
    ----------
    load_batch_size : int
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        load_batch_size = kwargs.pop('load_batch_size', None)

        super().__init__(**kwargs)

        self.load_batch_size = load_batch_size

    def validate_targets(self):
        super().validate_targets()

        if self.resolve_mode != 'skip' and self.bad_targets:
            msg = 'Twitter API says target(s) nonexistent/suspended/bad: {0}'
            msg = msg.format(', '.join([str(s) for s in self.bad_targets]))

            if self.allow_api_errors:
                logger.warning(msg)
            else:
                raise err.BadTargetError(message=msg, targets=self.bad_targets)


class RateLimitStatusJob(ApiJob):  # pylint: disable=too-few-public-methods
    '''
    Check the rate limits for the API keys in the config file.

    This job pulls the rate limit status for each key in the config file and
    prints it to stdout in json format. The job filters by default to only the
    API endpoints we use but can be told to show all of them.
    '''

    def __init__(self, **kwargs):
        full = kwargs.pop('full', False)
        consumer_key = kwargs.pop('consumer_key', None)

        super().__init__(**kwargs)

        self.full = full
        self.consumer_key = consumer_key

    def run(self):
        status = next(self.api.rate_limit_status())

        if not self.full:
            endpoints = ['/application/rate_limit_status', '/followers/ids',
                         '/friends/ids', '/users/lookup', '/lists/show',
                         '/lists/members', '/statuses/user_timeline']

            short = {}
            for key, resp in status.items():
                short[key] = {}

                for endpoint in endpoints:
                    _, grp, _ = endpoint.split('/')
                    short[key][endpoint] = resp['resources'][grp][endpoint]

            status = short

        status = json.dumps(status, indent=4)
        print(status)


class CreateTagJob(TagJob):
    '''
    Create a user tag.

    This job creates a new user tag. If the tag already exists, nothing is done
    and no error is raised. The tag is not applied to any users. (See
    ApplyTagJob for that.)
    '''

    def run(self):
        self.get_or_create(md.Tag, name=self.tag)

        self.session.commit()


class DeleteTagJob(TagJob):
    '''
    Delete a user tag.

    This job deletes a user tag. If the tag does not exist, nothing is done and
    no error is raised. Any existing assignments of the tag to users are also
    deleted.
    '''

    def run(self):
        tag = self.session.query(md.Tag).filter_by(name=self.tag).one_or_none()

        if tag:
            # DELETE is slow on many databases, but we're assuming none of
            # these lists are especially large - a few thousand rows, tops.
            # follow graph jobs have at least potentially really large data
            # and need to rely on DROP TABLE / CREATE TABLE (see below).
            self.session.delete(tag)

            self.session.commit()


class ApplyTagJob(TagJob, TargetJob):
    '''
    Apply a user tag to a set of users.

    This job applies an existing user tag to a set of users. If the tag does
    not exist, error.BadTagError is raised. (Use CreateTagJob to create a new
    tag.) The targets are resolved to users with ``resolve_mode == 'skip'``
    (i.e., any requested users which do not exist in the database are not
    looked up from the Twitter API). If any users were not successfully
    resolved, error.BadTargetError is raised unless the allow_missing_targets
    parameter is True. Otherwise, any users which were successfully resolved
    from the targets are given the tag. In particular, if no users were
    successfully resolved and allow_missing_users is True, nothing is done and
    no error is raised. The entire job is run as one transaction; if anything
    goes wrong, no tags are applied.
    '''

    resolve_mode = 'skip'

    def run(self):
        self.resolve_targets()

        tag = self.session.query(md.Tag).filter_by(name=self.tag).one_or_none()

        if not tag:
            msg = f'Tag {self.tag} does not exist'
            raise err.BadTagError(message=msg, tag=tag)

        for user in self.users:
            user.tags.append(tag)

        self.session.commit()


class InitializeJob(DatabaseJob):
    '''
    A job which initializes the selected database and sets up the schema.

    WARNING! This job will drop all data in the selected database! This job
    (re-)initializes the selected database and applies the schema to it. The
    version of the creating package will also be stored to help future versions
    with migrations and compatibility checks.
    '''

    def run(self):
        md.Base.metadata.drop_all(self.engine)
        md.Base.metadata.create_all(self.engine)

        self.session.add(md.SchemaVersion(version=__version__))
        self.session.commit()


class UserInfoJob(FetchJob):
    '''
    A job which hydrates users.

    This job resolves its targets to users with ``resolve_mode == 'hydrate'``.
    That is, it fetches data on those users from Twitter's ``users/lookup``
    endpoint, and stores the resulting data in the database. No other work is
    done. The entire job is run in one transaction; if anything goes wrong, no
    users are loaded.
    '''

    resolve_mode = 'hydrate'

    def run(self):
        self.resolve_targets()

        self.session.commit()


class TweetsJob(FetchJob):
    '''
    Fetch user tweets from the Twitter API.

    This job fetches user tweets from Twitter's statuses/user_timeline endpoint
    and loads them to the database. Several options are provided to control
    which of a given user's tweets are loaded. The loaded tweets are
    extensively normalized to extract other entities (mentions, mentioned
    users, hashtags, photos and videos, etc). The job is run in one transaction
    per user; if anything goes wrong during loading of a user, the user which
    encountered the error will be rolled back but tweets for previously
    processed users will remain in the database.

    Parameters
    ----------
    since_timestamp : float, or None
        A Unix timestamp. Tweets older than this will not be loaded, and an
        attempt will be made not to fetch them from the API in order to
        minimize usage of rate-limited endpoints.

    max_tweets : int, or None
        Stop loading tweets for each user after this many. If None, load all
        available tweets. After loading max_tweets tweets, no further calls to
        the Twitter endpoint will be made (to minimize usage of rate-limited
        endpoints).

    old_tweets : bool
        Should we, for each user, fetch only tweets newer than the newest one
        in the database (if False, default), or fetch all tweets (if True)?
        This can be done efficiently thanks to the Twitter endpoint's since_id
        parameter and the fact that tweet IDs are sequential.

    Attributes
    ----------
    since_timestamp : float
        The parameter passed to __init__.

    max_tweets : int
        The parameter passed to __init__.

    old_tweets : bool
        The parameter passed to __init__.
    '''

    resolve_mode = 'skip'

    def __init__(self, **kwargs):
        since_timestamp = kwargs.pop('since_timestamp', None)
        max_tweets = kwargs.pop('max_tweets', None)
        old_tweets = kwargs.pop('old_tweets', False)

        super().__init__(**kwargs)

        self.since_timestamp = since_timestamp
        self.max_tweets = max_tweets
        self.old_tweets = old_tweets

    def _load_tweets_for(self, user):
        if self.old_tweets:
            since_id = None
        else:
            since_id = self.session.query(sa.func.max(md.Tweet.tweet_id)) \
                           .filter(md.Tweet.user_id == user.user_id).scalar()

        twargs = {
            'user_id': user.user_id,
            'since_id': since_id,
            'max_tweets': self.max_tweets,
            'since_timestamp': self.since_timestamp
        }

        tweets = self.api.user_timeline(**twargs)
        tweets = ut.grouper(tweets, self.load_batch_size)

        n_items = 0
        for ind, batch in enumerate(tweets):
            msg = 'Running {0} batch {1}, within-user cumulative tweets {2}'
            msg = msg.format(type(self), ind + 1, n_items)
            logger.debug(msg)

            for resp in batch:
                tweet = md.Tweet.from_tweepy(resp, self.session)

                # The merge emits warnings about having disabled the
                # save-update cascade on Hashtag, Url, Symbol and Media,
                # which is intentional and not appropriate to show users.
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', category=sa.exc.SAWarning)
                    self.session.merge(tweet)

                n_items += 1

        return n_items

    def run(self):
        self.resolve_targets()

        n_items = 0
        for ind, user in enumerate(self.users):
            msg = 'Processing user_id {0} ({1} / {2}), ' \
                  'across-user cumulative tweets {3}'
            msg = msg.format(user.user_id, ind + 1, len(self.users), n_items)
            logger.info(msg)

            try:
                n_items += self._load_tweets_for(user)
            except (err.ForbiddenError, err.NotFoundError) as exc:
                if isinstance(exc, err.ForbiddenError):
                    msg = 'Encountered protected user (user_id {0}) in {1}'
                else:  # isinstance(e, err.NotFoundError)
                    # Twitter's API docs about errors don't capture all the
                    # actual behavior, so it's hard to tell what is and what
                    # isn't a protected user
                    msg = 'Encountered nonexistent (possibly protected) user (user_id {0}) in {1}'
                msg = msg.format(user.user_id, self.__class__.__name__)

                if self.allow_api_errors:
                    logger.warning(msg)
                else:
                    self.session.rollback()

                    raise err.BadTargetError(
                        message=msg,
                        targets=[user.user_id]
                    ) from exc
            else:
                self.session.commit()


# NOTE that here (unlike in TweetsJob), you can get gnarly primary key
# integrity errors on the user table if resolve_mode != 'skip': merging in
# an md.User object (but not flushing) and then running an insert against
# the user table may try to insert the same row again at commit if one of
# the User objects is for a row already loaded by the insert. (That is, if
# fetching users A and B, user B hadn't already been loaded and were
# hydrated here, and A follows B.) In this case, if this were not to be
# mode == 'skip' in the future, the easy thing to do is call
# self.session.flush() afterward. Note also that this only applies if the
# _load_edges_for steps don't implicitly commit, which they do on most DBs.
# (See the comments in that method.)
class FollowGraphJob(FetchJob):
    '''
    Fetch follow-graph edges from the Twitter API.

    This job fetches follow-graph edges from the Twitter API for a given set of
    users. Subclasses must specify which direction of edges to fetch (users'
    friends or followers). The edges are stored in the follow table, which uses
    a type 2 SCD format to allow tracking historical follow-graph state with
    reduced space requirements, and are first loaded to a staging table. The
    job is run in one transaction per user; if anything goes wrong during
    loading of a user, the user which encountered the error will be rolled back
    but edges for previously processed users will remain in the database.

    Note that Twitter sometimes returns the same follower/friend ID more
    than once (probably because of eventual consistency). As a result, there
    is special loading logic for these jobs. Each batch of follower or friend
    IDs is deduped before being inserted (the entire set of IDs at once if
    load_batch_size is None); if an ID in one batch duplicates an ID received
    in a previous batch, the batch is retried one row at a time (which is quite
    slow). Consequently loading these rows is most efficient with
    load_batch_size of None. Other values should be used only if memory is a
    constraint.
    '''

    resolve_mode = 'skip'

    @property
    @abstractmethod
    def direction(self):
        '''
        The "direction" of follow edges to load.

        Given a set of users, we might want to fetch the users who follow them
        (their "followers") or the users they follow (their "friends"). This
        attribute, which subclasses must set, should be either "friends" or
        "followers" to specify which direction of fetch is intended.
        '''

        raise NotImplementedError()

    @property
    @abstractmethod
    def _api_data_column(self):
        raise NotImplementedError()

    @property
    def _target_user_column(self):
        cols = {'source_user_id', 'target_user_id'}
        return list(cols - {self._api_data_column})[0]

    @property
    def _api_method_name(self):
        return self.direction + '_ids'

    # NOTE tl;dr the commit semantics here are complicated and depend on the
    # database, but the details shouldn't matter. Depending on the DB, clearing
    # the stg table may or may not commit; self._insert_stg_batch may issue one
    # or many commits. BUT both of these affect only data in the stg table; if
    # an error leaves it in an inconsistent state, we don't care. (If the
    # resolve_mode for this job were 'fetch', we'd also have to consider
    # whether and when any new users' rows were committed.) Whether there are 0
    # or more than 0 commits up to the end of the for loop below, there aren't
    # any during the call to _process_stg_data_for, which is the only part of
    # this that modifies main data tables. So that call happens atomically,
    # which is what we care about.
    def _load_edges_for(self, user):
        api_method = getattr(self.api, self._api_method_name)

        ids = api_method(user_id=user.user_id)
        ids = ut.grouper(ids, self.load_batch_size)

        self._clear_stg_table()

        n_items = 0
        for ind, batch in enumerate(ids):
            msg = 'Running {0} batch {1}, within-user cumulative edges {2}'
            msg = msg.format(type(self), ind + 1, n_items)
            logger.debug(msg)

            n_items += self._insert_stg_batch(user, batch)

        self._process_stg_data_for(user)

        return n_items

    # this is much, much faster than .delete() / DELETE FROM <tbl>, but not
    # transactional on many DBs
    def _clear_stg_table(self):
        md.StgFollow.__table__.drop(self.session.get_bind())
        md.StgFollow.__table__.create(self.session.get_bind())

    def _insert_stg_batch(self, user, api_user_ids):
        api_user_ids = set(api_user_ids)

        rows = (
            {self._api_data_column: t, self._target_user_column: user.user_id}
            for t in api_user_ids
        )

        try:
            self.session.bulk_insert_mappings(md.StgFollow, rows)
        except sa.exc.IntegrityError:
            self.session.rollback()
            logger.info('Working around duplicates in Twitter API response')

            # issues a commit for every row
            n_items = self._insert_stg_batch_robust(user, api_user_ids)
        else:
            n_items = len(api_user_ids)
            self.session.commit()

        return n_items

    # NOTE Twitter sometimes returns the same ID more than once.
    # This happens rarely (probably b/c of eventual consistency), so we
    # don't need to worry too hard about performance in handling it.
    # Thus: use bulk inserts, but catch the duplicate key error and,
    # when handling it, re-attempt inserts of the same rows one by one,
    # discarding any that raise the duplicate key error.
    def _insert_stg_batch_robust(self, user, api_user_ids):
        nrows = 0

        for api_uid in api_user_ids:
            row = {
                self._api_data_column: api_uid,
                self._target_user_column: user.user_id
            }

            try:
                ins = md.StgFollow.__table__.insert().values(**row)
                self.session.execute(ins)

                nrows += 1
            except sa.exc.IntegrityError:
                self.session.rollback()

                msg = 'Encountered IntegrityError (likely dupe) on edge {0}'
                msg = msg.format(row)

                logger.debug(msg)
            else:
                self.session.commit()

        return nrows

    def _process_stg_data_for(self, user):
        #
        # 1. Load any new users to user table
        #

        flt = self.session.query(md.User).filter(
            md.User.user_id == getattr(md.StgFollow, self._api_data_column)
        ).correlate(md.StgFollow)

        # We don't need to worry about inserting the same user_id value
        # that's already in the user.user_id object (and causing a primary
        # key integrity error on the user table) because that user_id is
        # already in the self._target_user_column column; it would only also
        # appear in the self._api_data_column column if you could follow
        # yourself on Twitter, which you can't.
        ins = md.User.__table__.insert().from_select(
            ['user_id'],
            self.session.query(
                getattr(md.StgFollow, self._api_data_column)
            ).filter(~flt.exists())
        )

        self.session.execute(ins)

        #
        # 2. Load new edges to follow table with valid_end_dt of null
        #

        flt = self.session.query(md.Follow).filter(sa.and_(
            md.Follow.valid_end_dt.is_(None),
            md.Follow.source_user_id == md.StgFollow.source_user_id,
            md.Follow.target_user_id == md.StgFollow.target_user_id
        )).correlate(md.StgFollow)

        ins = md.Follow.__table__.insert().from_select(
            ['source_user_id', 'target_user_id'],
            self.session.query(
                md.StgFollow.source_user_id,
                md.StgFollow.target_user_id
            ).filter(~flt.exists())
        )

        self.session.execute(ins)

        #
        # 3. Mark edges no longer present as expired (valid_end_dt := now())
        #

        flt = self.session.query(md.StgFollow).filter(sa.and_(
            md.StgFollow.source_user_id == md.Follow.source_user_id,
            md.StgFollow.target_user_id == md.Follow.target_user_id
        )).correlate(md.Follow)

        upd = md.Follow.__table__.update().where(sa.and_(
            md.Follow.valid_end_dt.is_(None),
            getattr(md.Follow, self._target_user_column) == user.user_id,

            ~flt.exists()
        )).values(valid_end_dt=sa.func.now())

        self.session.execute(upd)

    def run(self):
        self.resolve_targets()

        n_items = 0
        for ind, user in enumerate(self.users):
            msg = 'Processing user_id {0} ({1} / {2}), ' \
                  'across-user cumulative edges {3}'
            msg = msg.format(user.user_id, ind + 1, len(self.users), n_items)
            logger.info(msg)

            try:
                n_items += self._load_edges_for(user)
            except (err.ForbiddenError, err.NotFoundError) as exc:
                if isinstance(exc, err.ForbiddenError):
                    msg = 'Encountered protected user with user_id {0} in {1}'
                else:  # isinstance(e, err.NotFoundError)
                    pass
                msg = msg.format(user.user_id, self.__class__.__name__)

                if self.allow_api_errors:
                    logger.warning(msg)
                else:
                    self.session.rollback()

                    raise err.BadTargetError(
                        message=msg,
                        targets=[user.user_id]
                    ) from exc
            else:
                self.session.commit()


class FollowersJob(FollowGraphJob):
    '''
    A FollowGraphJob which fetches user followers.
    '''

    direction = 'followers'
    _api_data_column = 'source_user_id'


class FriendsJob(FollowGraphJob):
    '''
    A FollowGraphJob which fetches user friends.
    '''

    direction = 'friends'
    _api_data_column = 'target_user_id'
