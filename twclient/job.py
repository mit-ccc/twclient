import random
import logging
import warnings
import itertools as it

from abc import ABC, abstractmethod

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from . import __version__
from . import error as err
from . import utils as ut
from . import models as md
from . import twitter_api as ta

logger = logging.getLogger(__name__)

##
## Job classes
## These encapsulate different types of loading jobs, including
## the details of interacting with the database and Twitter API
##

class Job(ABC):
    def __init__(self, **kwargs):
        try:
            engine = kwargs.pop('engine')
        except KeyError:
            raise ValueError("engine instance is required")

        super(Job, self).__init__(**kwargs)

        self.engine = engine

        self.sessionfactory = sessionmaker()
        self.sessionfactory.configure(bind=self.engine)
        self.session = self.sessionfactory()

        self._schema_verified = False

    def ensure_schema_version(self):
        if self._schema_verified:
            return

        schema_version = self.session.query(md.SchemaVersion).all()

        if len(schema_version) != 1:
            msg = 'Bad or missing schema version tag in database'
            raise err.BadSchemaError(message=msg)

        db_version = schema_version[0].version

        if db_version > __version__:
            msg = 'Package version {0} cannot use future schema version {1}'
            msg = msg.format(__version__, db_version)
            raise err.BadSchemaError(message=msg)

        if db_version < __version__:
            msg= 'Package version {0} cannot migrate old schema version {1}; ' \
                 'consider downgrading the package version'
            msg = msg.format(__version__, db_version)
            raise err.BadSchemaError(message=msg)

        self._schema_verified = True

    def get_or_create(self, model, **kwargs):
        instance = self.session.query(model).filter_by(**kwargs).one_or_none()

        if instance:
            return instance
        else:
            instance = model(**kwargs)

            self.session.add(instance)

            return instance

    @abstractmethod
    def run(self):
        raise NotImplementedError()

class TagJob(Job):
    def __init__(self, **kwargs):
        try:
            tag = kwargs.pop('tag')
        except KeyError:
            raise ValueError('Must provide tag argument')

        super(TagJob, self).__init__(**kwargs)

        self.tag = tag

        self.ensure_schema_version()

class TargetJob(Job):
    def __init__(self, **kwargs):
        try:
            targets = kwargs.pop('targets')
        except KeyError:
            raise ValueError('Must provide list of targets')

        allow_missing_targets = kwargs.pop('allow_missing_targets', False)

        super(TargetJob, self).__init__(**kwargs)

        self.targets = targets
        self.allow_missing_targets = allow_missing_targets

        self.ensure_schema_version()

    @property
    @abstractmethod
    def resolve_mode(self):
        raise NotImplementedError()

    @property
    def resolved(self):
        return all([t.resolved for t in self.targets])

    def _combine_sub_attrs(self, attr):
        if not self.resolved:
            raise AttributeError('Must call resolve_targets() first')

        objs = it.chain(*[getattr(t, attr) for t in self.targets])
        return [u for u in objs]

    @property
    def users(self):
        return self._combine_sub_attrs('users')

    @property
    def bad_targets(self):
        return self._combine_sub_attrs('bad_targets')

    @property
    def missing_targets(self):
        return self._combine_sub_attrs('missing_targets')

    def resolve_targets(self):
        for target in self.targets:
            target.resolve(context=self)

        self.validate_targets()

    def validate_targets(self):
        if self.resolve_mode == 'skip' and len(self.missing_targets) > 0:
            msg = 'Target(s) not in database: {0}'
            msg = msg.format(', '.join(self.missing_targets))

            if not self.allow_missing_targets:
                raise err.BadTargetError(message=msg, targets=self.missing_targets)
            else:
                logger.warning(msg)

class ApiJob(TargetJob):
    def __init__(self, **kwargs):
        try:
            api = kwargs.pop('api')
        except KeyError:
            raise ValueError('Must provide api object')

        allow_api_errors = kwargs.pop('allow_api_errors', False)
        load_batch_size = kwargs.pop('load_batch_size', 10000)

        super(ApiJob, self).__init__(**kwargs)

        self.api = api
        self.load_batch_size = load_batch_size
        self.allow_api_errors = allow_api_errors

    def validate_targets(self):
        super(ApiJob, self).validate_targets()

        if self.resolve_mode != 'skip' and len(self.bad_targets) > 0:
            msg = 'Twitter API says target(s) nonexistent/suspended/bad: {0}'
            msg = msg.format(', '.join(self.bad_targets))

            if not self.allow_api_errors:
                raise err.BadTargetError(message=msg, targets=self.bad_targets)
            else:
                logger.warning(msg)

class CreateTagJob(TagJob):
    def run(self):
        self.get_or_create(md.Tag, name=self.tag)

        self.session.commit()

class DeleteTagJob(TagJob):
    def run(self):
        tag = self.session.query(md.Tag).filter_by(name=self.tag).one_or_none()

        if tag:
            # DELETE is slow on many databases, but we're assuming none of these
            # lists are especially large - a few thousand rows, tops. follow
            # graph jobs have at least potentially really large data and need to
            # rely on DROP TABLE / CREATE TABLE (see below).
            self.session.query(md.UserTag).filter_by(tag_id=tag.tag_id).delete()
            self.session.delete(tag)

            self.session.commit()

class ApplyTagJob(TagJob, TargetJob):
    resolve_mode = 'skip'

    def run(self):
        self.resolve_targets()

        tag = self.session.query(md.Tag).filter_by(name=self.tag).one_or_none()

        if not tag:
            msg = 'Tag {0} does not exist'.format(self.tag)
            raise err.BadTagError(message=msg, tag=tag)

        for user in self.users:
            user.tags.append(tag)

        self.session.commit()

class InitializeJob(Job):
    def run(self):
        md.Base.metadata.drop_all(self.engine)
        md.Base.metadata.create_all(self.engine)

        self.session.add(md.SchemaVersion(version=__version__))
        self.session.commit()

class UserInfoJob(ApiJob):
    resolve_mode = 'hydrate'

    def run(self):
        self.resolve_targets()

        self.session.commit()

class TweetsJob(ApiJob):
    resolve_mode = 'skip'

    def __init__(self, **kwargs):
        since_timestamp = kwargs.pop('since_timestamp', None)
        max_tweets = kwargs.pop('max_tweets', None)
        old_tweets = kwargs.pop('old_tweets', False)

        super(TweetsJob, self).__init__(**kwargs)

        self.since_timestamp = since_timestamp
        self.max_tweets = max_tweets
        self.old_tweets = old_tweets

    def load_tweets_for(self, user):
        if self.old_tweets:
            since_id = None
        else:
            since_id = self.session.query(sa.func.max(md.Tweet.tweet_id)) \
                           .filter(md.Tweet.user_id==user.user_id).scalar()

        twargs = {
            'user_id': user.user_id,
            'since_id': since_id,
            'max_tweets': self.max_tweets,
            'since_timestamp': self.since_timestamp
        }

        tweets = self.api.user_timeline(**twargs)
        tweets = ut.grouper(tweets, self.load_batch_size)

        n_items = 0
        for i, batch in enumerate(tweets):
            msg = 'Running {0} batch {1}, within-user cumulative tweets {2}'
            msg = msg.format(type(self), i + 1, n_items)
            logger.debug(msg)

            for resp in batch:
                tweet = md.Tweet.from_tweepy(resp, self.session)

                # The merge emits warnings about having disabled the
                # save-update cascade on Hashtag, Url, Symbol and Media,
                # which is intentional and not appropriate to show users.
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', category=sa.exc.SAWarning)
                    self.session.merge(tweet)

            n_items += len(batch)

        return n_items

    def run(self):
        self.resolve_targets()

        n_items = 0
        for i, user in enumerate(self.users):
            msg = 'Processing user_id {0} ({1} / {2}), ' \
                  'across-user cumulative tweets {3}'
            msg = msg.format(user.user_id, i + 1, len(self.users), n_items)
            logger.info(msg)

            try:
                n_items += self.load_tweets_for(user)
            except err.ProtectedUserError as e:
                msg = 'Encountered protected user with user_id {0} in {1}'
                msg = msg.format(user.user_id, self.__class__.__name__)

                if not self.allow_api_errors:
                    self.session.rollback()
                    raise err.BadTargetError(message=msg, targets=[user.user_id])
                else:
                    logger.warning(msg)
            except err.NotFoundError as e:
                msg = 'Encountered nonexistent user with user_id {0} in {1}'
                msg = msg.format(user.user_id, self.__class__.__name__)

                if not self.allow_api_errors:
                    self.session.rollback()
                    raise err.BadTargetError(message=msg, targets=[user.user_id])
                else:
                    logger.warning(msg)
            else:
                self.session.commit()

class FollowGraphJob(ApiJob):
    # NOTE that here (unlike in TweetsJob), you can get gnarly primary key
    # integrity errors on the user table if resolve_mode != 'skip': merging in
    # an md.User object (but not flushing) and then running an insert against
    # the user table may try to insert the same row again at commit if one of
    # the User objects is for a row already loaded by the insert. (That is, if
    # fetching users A and B, user B hadn't already been loaded and were
    # hydrated here, and A follows B.) In this case, if this were not to be
    # mode == 'skip' in the future, the easy thing to do is call
    # self.session.flush() afterward. Note also that this only applies if the
    # load_edges_for steps don't implicitly commit, which they do on most DBs.
    # (See the comments in that method.)
    resolve_mode = 'skip'

    def __init__(self, **kwargs):
        fast_load = kwargs.pop('fast_load', False)

        super(FollowGraphJob, self).__init__(**kwargs)

        self.fast_load = fast_load

    @property
    @abstractmethod
    def direction(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def api_data_column(self):
        raise NotImplementedError()

    @property
    def api_method_name(self):
        return self.direction + '_ids'

    @property
    def target_user_column(self):
        cols = {'source_user_id', 'target_user_id'}
        return list(cols - {self.api_data_column})[0]

    @property
    def api_method(self):
        return getattr(self.api, self.api_method_name)

    def load_edges_for(self, user):
        ids = self.api_method(user_id=user.user_id)
        ids = ut.grouper(ids, self.load_batch_size)

        # NOTE tl;dr the commit semantics here are complicated and depend on the
        # database, but the details shouldn't matter. Depending on the DB,
        # clearing the stg table may or may not commit; depending on the setting
        # of self.fast_load, self.insert_stg_batch may or may not do so as well.
        # BUT both of these affect only data in the stg table; if an error
        # leaves it in an inconsistent state, we don't care. (If the
        # resolve_mode for this job were 'fetch', we'd also have to consider
        # whether and when any new users' rows were committed.) Whether there
        # are 0 or more than 0 commits up to the end of the for loop below,
        # there aren't any during the call to process_stg_data_for, which is the
        # only part of this that modifies main data tables. So that call happens
        # atomically, which is what we care about.

        self.clear_stg_table()

        n_items = 0
        for j, batch in enumerate(ids):
            msg = 'Running {0} batch {1}, within-user cumulative edges {2}'
            msg = msg.format(type(self), j + 1, n_items)
            logger.debug(msg)

            n_items += self.insert_stg_batch(user, batch)

        self.process_stg_data_for(user)

        return n_items

    def clear_stg_table(self):
        # this is much, much faster than .delete() / DELETE FROM <tbl>, but not
        # transactional on many DBs
        md.StgFollow.__table__.drop(self.session.get_bind())
        md.StgFollow.__table__.create(self.session.get_bind())

    def insert_stg_batch(self, user, api_user_ids):
        rows = [
            {self.api_data_column: t, self.target_user_column: user.user_id}
            for t in api_user_ids
        ]

        try:
            self.session.bulk_insert_mappings(md.StgFollow, rows)
        except sa.exc.IntegrityError:
            self.session.rollback()

            if not self.fast_load:
                n_items = self.insert_stg_batch_robust(rows)
            else:
                raise
        else:
            n_items = len(rows)

        # NOTE committing slows things down, but without it, we'd lose every
        # row loaded before one of these duplicate key problems
        if not self.fast_load:
            self.session.commit()

        return n_items

    def insert_stg_batch_robust(self, rows):
        nrows = 0

        # NOTE Twitter sometimes returns the same ID more than once.
        # This happens rarely (probably b/c of eventual consistency), so we
        # don't need to worry too hard about performance in handling it.
        # Thus: use bulk inserts, but catch the duplicate key error and,
        # when handling it, re-attempt inserts of the same rows one by one,
        # discarding any that raise the duplicate key error.
        for row in rows:
            try:
                md.StgFollow.__table__.insert().values(**row)
                nrows += 1
            except sa.exc.IntegrityError:
                msg = 'Encountered IntegrityError (likely dupe) on edge {0}'
                logger.debug(msg.format(row))

        return nrows

    def process_stg_data_for(self, user):
        ##
        ## 1. Load any new users to user table
        ##

        flt = self.session.query(md.User).filter(
            md.User.user_id == getattr(md.StgFollow, self.api_data_column)
        ).correlate(md.StgFollow)

        # We don't need to worry about inserting the same user_id value
        # that's already in the user.user_id object (and causing a primary
        # key integrity error on the user table) because that user_id is
        # already in the self.target_user_column column; it would only also
        # appear in the self.api_data_column column if you could follow
        # yourself on Twitter, which you can't.
        ins = md.User.__table__.insert().from_select(
            ['user_id'],
            self.session.query(
                getattr(md.StgFollow, self.api_data_column)
            ).filter(~flt.exists())
        )

        self.session.execute(ins)

        ##
        ## 2. Load new edges to follow table with valid_end_dt of null
        ##

        flt = self.session.query(md.Follow).filter(sa.and_(
            md.Follow.valid_end_dt == None,
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

        ##
        ## 3. Mark edges no longer present as expired (valid_end_dt := now())
        ##

        flt = self.session.query(md.StgFollow).filter(sa.and_(
            md.StgFollow.source_user_id == md.Follow.source_user_id,
            md.StgFollow.target_user_id == md.Follow.target_user_id
        )).correlate(md.Follow)

        upd = md.Follow.__table__.update().where(sa.and_(
            md.Follow.valid_end_dt == None,
            getattr(md.Follow, self.target_user_column) == user.user_id,

            ~flt.exists()
        )).values(valid_end_dt=sa.func.now())

        self.session.execute(upd)

    def run(self):
        self.resolve_targets()

        n_items = 0
        for i, user in enumerate(self.users):
            msg = 'Processing user_id {0} ({1} / {2}), ' \
                  'across-user cumulative edges {3}'
            msg = msg.format(user.user_id, i + 1, len(self.users), n_items)
            logger.info(msg)

            try:
                n_items += self.load_edges_for(user)
            except err.ProtectedUserError as e:
                msg = 'Encountered protected user with user_id {0} in {1}'
                msg = msg.format(user.user_id, self.__class__.__name__)

                if not self.allow_api_errors:
                    self.session.rollback()
                    raise err.BadTargetError(message=msg, targets=[user.user_id])
                else:
                    logger.warning(msg)
            except err.NotFoundError as e:
                msg = 'Encountered nonexistent user with user_id {0} in {1}'
                msg = msg.format(user.user_id, self.__class__.__name__)

                if not self.allow_api_errors:
                    self.session.rollback()
                    raise err.BadTargetError(message=msg, targets=[user.user_id])
                else:
                    logger.warning(msg)
            else:
                self.session.commit()

class FollowersJob(FollowGraphJob):
    direction = 'followers'
    api_data_column = 'source_user_id'

class FriendsJob(FollowGraphJob):
    direction = 'friends'
    api_data_column = 'target_user_id'

