import random
import logging
import itertools as it

from abc import ABC, abstractmethod

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

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

class CreateTagJob(TagJob):
    def run(self):
        self.get_or_create(md.Tag, name=self.tag)

        self.session.commit()

class DeleteTagJob(TagJob):
    def run(self):
        tag = self.session.query(md.Tag).filter_by(name=self.tag).one_or_none()

        if tag:
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
            target.resolve(context=self, mode='raise_missing')

        users = [u for u in it.chain(*[t.users for t in self.targets])]

        tag = self.session.query(md.Tag).filter_by(name=self.tag).one()

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
            target.resolve(context=self, mode='raise_missing')

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
    def api_method_name(self):
        return self.direction + '_ids'

    @property
    def api_method(self):
        return getattr(self.api, self.api_method_name)

    def run(self):
        for target in self.targets:
            target.resolve(context=self, mode='raise_missing')

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

            for j, batch in enumerate(ids):
                msg = 'Running {0} batch {1}, cumulative edges {2}'
                msg = msg.format(type(self), j + 1, n_items)
                logger.debug(msg)

                self.session.bulk_save_objects([
                    md.StgFollow(user_id=t)
                    for t in batch
                ])

                n_items += len(batch)

            # FIXME

            self.session.commit()

class FollowersJob(FollowGraphJob):
    direction = 'followers'

class FriendsJob(FollowGraphJob):
    direction = 'friends'

