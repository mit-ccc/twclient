'''
Jobs which interact with the Twitter API.
'''

import random
import logging
import warnings

from abc import abstractmethod

import sqlalchemy as sa

from ._job_base import TargetJob, ApiJob
from .error import BadTargetError, ForbiddenError, NotFoundError
from ._utils import grouper, export
from .models import User, Follow, StgFollow, Tweet

logger = logging.getLogger(__name__)

# This isn't a great way to handle these warnings, but sqlalchemy is so dynamic
# that most attribute accesses aren't resolved until runtime
# pylint: disable=no-member


# this is just a stub to placate the linter; the @export decorator adds
# objects to __all__ so that whether an object is included is noted next to it
__all__ = []

@export
class FetchJob(ApiJob, TargetJob):
    '''
    A job fetching data from the Twitter API.

    This class represents a job which fetches data from the Twitter API. It
    configures API access and user validation logic, and defers other
    functionality to subclasses.

    Parameters
    ----------
        load_batch_size : int
            Load new rows to the database in batches of this size. The default
            is None, which loads all data retrieved in one batch. Lower values
            minimize memory usage at the cost of slower loading speeds, while
            higher values do the reverse. Target instances in self.targets do
            not consider this value--it applies only to other rows loaded by
            the FetchJob instance--because there are generally not enough
            targets to consume a significant amount of memory. Followers and
            friends lists in particular can be large enough to cause
            out-of-memory conditions; setting ``load_batch_size`` to an
            appropriate value (e.g., 5000) can address this problem.

        randomize : bool
            Whether to process raw targets in a randomized order. This may
            allow loads which are interrupted partway through to retain some
            useful statistical properties.

    Attributes
    ----------
        load_batch_size : int
            The parameter passed to __init__.

        randomize : bool
            The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        load_batch_size = kwargs.pop('load_batch_size', None)
        randomize = kwargs.pop('randomize', False)

        super().__init__(**kwargs)

        self.load_batch_size = load_batch_size
        self.randomize = randomize

        self._users = None

    @property
    def users(self):
        if not self.randomize:
            return super().users

        if self._users is None:
            self._users = super().users
            random.shuffle(self._users)

        return self._users

    def validate_targets(self):
        super().validate_targets()

        if self.resolve_mode != 'skip' and self.bad_targets:
            msg = 'Twitter API says target(s) nonexistent/suspended/bad: {0}'
            msg = msg.format(', '.join([str(s) for s in self.bad_targets]))

            if self.allow_api_errors:
                logger.warning(msg)
            else:
                raise BadTargetError(message=msg, targets=self.bad_targets)


@export
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


@export
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
            since_id = self.session.query(sa.func.max(Tweet.tweet_id)) \
                           .filter(Tweet.user_id == user.user_id).scalar()

        twargs = {
            'user_id': user.user_id,
            'since_id': since_id,
            'max_tweets': self.max_tweets,
            'since_timestamp': self.since_timestamp
        }

        tweets = self.api.user_timeline(**twargs)
        tweets = grouper(tweets, self.load_batch_size)

        n_items = 0
        for ind, batch in enumerate(tweets):
            msg = 'Running {0} batch {1}, within-user cumulative tweets {2}'
            msg = msg.format(type(self), ind + 1, n_items)
            logger.debug(msg)

            for resp in batch:
                tweet = Tweet.from_tweepy(resp, self.session)

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
            except (ForbiddenError, NotFoundError) as exc:
                if isinstance(exc, ForbiddenError):
                    msg = 'Encountered protected user (user_id {0}) in {1}'
                else:  # isinstance(e, NotFoundError)
                    # Twitter's API docs about errors don't capture all the
                    # actual behavior, so it's hard to tell what is and what
                    # isn't a protected user
                    msg = 'Encountered nonexistent (possibly protected) user (user_id {0}) in {1}'
                msg = msg.format(user.user_id, self.__class__.__name__)

                if self.allow_api_errors:
                    logger.warning(msg)
                else:
                    self.session.rollback()

                    raise BadTargetError(
                        message=msg,
                        targets=[user.user_id]
                    ) from exc
            else:
                self.session.commit()


# NOTE that here (unlike in TweetsJob), you can get gnarly primary key
# integrity errors on the user table if resolve_mode != 'skip': merging in
# a User object (but not flushing) and then running an insert against
# the user table may try to insert the same row again at commit if one of
# the User objects is for a row already loaded by the insert. (That is, if
# fetching users A and B, user B hadn't already been loaded and were
# hydrated here, and A follows B.) In this case, if this were not to be
# mode == 'skip' in the future, the easy thing to do is call
# self.session.flush() afterward. Note also that this only applies if the
# _load_edges_for steps don't implicitly commit, which they do on most DBs.
# (See the comments in that method.)
@export
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
        ids = grouper(ids, self.load_batch_size)

        StgFollow.clear_fast(self.session)

        n_items = 0
        for ind, batch in enumerate(ids):
            msg = 'Running {0} batch {1}, within-user cumulative edges {2}'
            msg = msg.format(type(self), ind + 1, n_items)
            logger.debug(msg)

            n_items += self._insert_stg_batch(user, batch)

        self._process_stg_data_for(user)

        return n_items

    def _insert_stg_batch(self, user, api_user_ids):
        api_user_ids = set(api_user_ids)

        rows = (
            {self._api_data_column: t, self._target_user_column: user.user_id}
            for t in api_user_ids
        )

        try:
            self.session.bulk_insert_mappings(StgFollow, rows)
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
                ins = StgFollow.__table__.insert().values(**row)
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

        flt = self.session.query(User).filter(
            User.user_id == getattr(StgFollow, self._api_data_column)
        ).correlate(StgFollow)

        # We don't need to worry about inserting the same user_id value
        # that's already in the user.user_id object (and causing a primary
        # key integrity error on the user table) because that user_id is
        # already in the self._target_user_column column; it would only also
        # appear in the self._api_data_column column if you could follow
        # yourself on Twitter, which you can't.
        ins = User.__table__.insert().from_select(
            ['user_id'],
            self.session.query(
                getattr(StgFollow, self._api_data_column)
            ).filter(~flt.exists())
        )

        self.session.execute(ins)

        #
        # 2. Load new edges to follow table with valid_end_dt of null
        #

        flt = self.session.query(Follow).filter(sa.and_(
            Follow.valid_end_dt.is_(None),
            Follow.source_user_id == StgFollow.source_user_id,
            Follow.target_user_id == StgFollow.target_user_id
        )).correlate(StgFollow)

        ins = Follow.__table__.insert().from_select(
            ['source_user_id', 'target_user_id'],
            self.session.query(
                StgFollow.source_user_id,
                StgFollow.target_user_id
            ).filter(~flt.exists())
        )

        self.session.execute(ins)

        #
        # 3. Mark edges no longer present as expired (valid_end_dt := now())
        #

        flt = self.session.query(StgFollow).filter(sa.and_(
            StgFollow.source_user_id == Follow.source_user_id,
            StgFollow.target_user_id == Follow.target_user_id
        )).correlate(Follow)

        upd = Follow.__table__.update().where(sa.and_(
            Follow.valid_end_dt.is_(None),
            getattr(Follow, self._target_user_column) == user.user_id,

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
            except (ForbiddenError, NotFoundError) as exc:
                if isinstance(exc, ForbiddenError):
                    msg = 'Encountered protected user with user_id {0} in {1}'
                else:  # isinstance(e, NotFoundError)
                    pass
                msg = msg.format(user.user_id, self.__class__.__name__)

                if self.allow_api_errors:
                    logger.warning(msg)
                else:
                    self.session.rollback()

                    raise BadTargetError(
                        message=msg,
                        targets=[user.user_id]
                    ) from exc
            else:
                self.session.commit()


@export
class FollowersJob(FollowGraphJob):
    '''
    A FollowGraphJob which fetches user followers.
    '''

    direction = 'followers'
    _api_data_column = 'source_user_id'


@export
class FriendsJob(FollowGraphJob):
    '''
    A FollowGraphJob which fetches user friends.
    '''

    direction = 'friends'
    _api_data_column = 'target_user_id'
