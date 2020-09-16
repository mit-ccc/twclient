import random
import logging
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

        schema_version = self.session.query(md.SchemaVersion).all()

        if len(schema_version) != 1:
            msg = 'Bad or missing schema version tag in database'
            raise err.BadSchemaError(message=msg)

        db_version = schema_version[0].version

        if db_version > __version__:
            msg = 'Package version {0} cannot use future schema version {1}'
            raise err.BadSchemaError(message=msg.format(__version__, db_version)

        if db_version < __version__:
            msg= 'Package version {0} cannot migrate old schema version {1}; ' \
                 'consider downgrading the package version'
            raise err.BadSchemaError(message=msg.format(__version__, db_version)

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

class InitializeJob(Job):
    def run(self):
        md.Base.metadata.drop_all(self.engine)
        md.Base.metadata.create_all(self.engine)

        self.session.add(md.SchemaVersion(version=__version__))
        self.session.commit()

class TagJob(Job):
    def __init__(self, **kwargs):
        try:
            tag = kwargs.pop('tag')
        except KeyError:
            raise ValueError('Must provide tag argument')

        super(TagJob, self).__init__(**kwargs)

        self.tag = tag

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

class ApplyTagJob(TagJob):
    def __init__(self, **kwargs):
        try:
            targets = kwargs.pop('targets')
        except KeyError:
            raise ValueError('Must provide list of targets')

        super(ApplyTagJob, self).__init__(**kwargs)

        self.targets = targets

    def run(self):
        for target in self.targets:
            target.resolve(context=self, mode='raise')

        users = [u for u in it.chain(*[t.users for t in self.targets])]

        tag = self.session.query(md.Tag).filter_by(name=self.tag).one_or_none()
        if not tag:
            msg = 'Tag {0} does not exist'.format(self.tag)
            raise err.BadTargetError(message=msg)

        for user in users:
            user.tags.append(tag)

        self.session.commit()

class ApiJob(Job):
    def __init__(self, **kwargs):
        try:
            targets = kwargs.pop('targets')
        except KeyError:
            raise ValueError('Must provide list of targets')

        try:
            api = kwargs.pop('api')
        except KeyError:
            raise ValueError('Must provide api object')

        load_batch_size = kwargs.pop('load_batch_size', 5000)

        super(ApiJob, self).__init__(**kwargs)

        self.targets = targets
        self.api = api

        self.load_batch_size = load_batch_size

class UserInfoJob(ApiJob):
    def run(self):
        for target in self.targets:
            target.resolve(context=self, mode='rehydrate')

        self.session.commit()

class TweetsJob(ApiJob):
    def __init__(self, **kwargs):
        since_timestamp = kwargs.pop('since_timestamp', None)
        max_tweets = kwargs.pop('max_tweets', None)
        old_tweets = kwargs.pop('old_tweets', False)

        super(TweetsJob, self).__init__(**kwargs)

        self.since_timestamp = since_timestamp
        self.max_tweets = max_tweets
        self.old_tweets = old_tweets

    def run(self):
        for target in self.targets:
            target.resolve(context=self, mode='raise')

        users = [u for u in it.chain(*[t.users for t in self.targets])]

        n_items = 0
        for i, user in enumerate(users):
            msg = 'Processing user_id {0} ({1} / {2}), cumulative tweets {3}'
            logger.info(msg.format(user.user_id, i + 1, len(users), n_items))

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

            for j, batch in enumerate(tweets):
                msg = 'Running {0} batch {1}, cumulative tweets {2}'
                msg = msg.format(type(self), j + 1, n_items)
                logger.debug(msg)

                for resp in batch:
                    tweet = md.Tweet.from_tweepy(resp)

                    self.session.merge(tweet)

                n_items += len(batch)

            self.session.commit()

class FollowGraphJob(ApiJob):
    @property
    @abstractmethod
    def direction(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def api_data_column(self):
        raise NotImplementedError()

    @property
    def target_user_column(self):
        cols = {'source_user_id', 'target_user_id'}
        return list(cols - {self.api_data_column})[0]

    @property
    def api_method_name(self):
        return self.direction + '_ids'

    @property
    def api_method(self):
        return getattr(self.api, self.api_method_name)

    def run(self):
        for target in self.targets:
            # Note that here (unlike in TweetsJob), you can get gnarly primary
            # key integrity errors on the user table if this isn't mode='raise':
            # merging in an md.User object for a given user and then running an
            # insert against the user table may try to insert the same row again
            # at commit if one of the User objects is for a row already loaded
            # by the insert. (That is, if fetching users A and B, user B hadn't
            # already been loaded and were hydrated here, and A follows B.) In
            # this case, if this were not to be mode='raise' in the future, the
            # easy thing to do is call self.session.flush() afterward.
            target.resolve(context=self, mode='raise')

        users = [u for u in it.chain(*[t.users for t in self.targets])]

        n_items = 0
        for i, user in enumerate(users):
            msg = 'Processing user_id {0} ({1} / {2}), cumulative edges {3}'
            logger.info(msg.format(user.user_id, i + 1, len(users), n_items))

            ids = self.api_method(user_id=user.user_id)
            ids = ut.grouper(ids, self.load_batch_size)

            # clear the stg table - this is much faster than '.delete()'
            # but has the downside of not being transactional on many DBs
            md.StgFollow.__table__.drop(self.session.get_bind())
            md.StgFollow.__table__.create(self.session.get_bind())

            # FIXME twitter sometimes returns the same ID more than once.
            # the sensible thing to do here to preserve speed is keep this bulk
            # loading approach, but catch the duplicate key error and, when
            # handling it, re-attempt inserts of the same rows one-by-one,
            # discarding any that raise the duplicate key error. it's a rare
            # problem to get duplicate keys from the API (eventual consistency?)
            # so no need to worry too hard about optimizing it. if you can get
            # the rows that caused the error out of the exception object and
            # just ignore them, even better.
            for j, batch in enumerate(ids):
                msg = 'Running {0} batch {1}, cumulative edges {2}'
                msg = msg.format(type(self), j + 1, n_items)
                logger.debug(msg)

                self.session.bulk_insert_mappings(md.StgFollow,
                [
                    {
                        self.api_data_column: t,
                        self.target_user_column: user.user_id
                    }

                    for t in batch
                ])

                n_items += len(batch)

            # First, load the users
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

            # Next, insert rows in StgFollow lacking a row in Follow with
            # valid_end_dt of null
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

            # Lastly, update current Follow rows not found in StgFollow to set
            # their valid_end_dt column to now()
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

            self.session.commit()

class FollowersJob(FollowGraphJob):
    direction = 'followers'
    api_data_column = 'source_user_id'

class FriendsJob(FollowGraphJob):
    direction = 'friends'
    api_data_column = 'target_user_id'

