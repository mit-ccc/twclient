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
            targets = kwargs.pop('targets')
        except KeyError:
            raise ValueError('Must provide list of targets')

        try:
            engine = kwargs.pop('engine')
        except KeyError:
            raise ValueError("engine instance is required")

        try:
            api = kwargs.pop('api')
        except KeyError:
            raise ValueError('Must provide api object')

        user_tag = kwargs.pop('user_tag', None)
        load_batch_size = kwargs.pop('load_batch_size', None)
        onetxn = kwargs.pop('onetxn', False)

        super(Job, self).__init__(**kwargs)

        self.targets = targets
        self.engine = engine
        self.api = api

        self.user_tag = user_tag
        self.load_batch_size = load_batch_size
        self.onetxn = onetxn

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

class UserInfoJob(Job):
    def run(self):
        if self.user_tag is not None:
            tag = self.get_or_create(md.Tag, name=self.user_tag)

        for target in self.targets:
            target.resolve(context=self, mode='rehydrate')

            for user in target.users:
                if self.user_tag is not None:
                    user.tags.append(tag)

        self.session.commit()

class TweetsJob(Job):
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
            target.resolve(context=self, mode='fetch') # FIXME should this be fetch? here and elsewhere

        users = it.chain(*[t.users for t in self.targets])

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

                if not self.onetxn:
                    self.session.commit()

                n_items += len(batch)

        if self.onetxn:
            self.session.commit()

class FollowJob(Job):
    def __init__(self, **kwargs):
        try:
            direction = kwargs.pop('direction')

            assert direction in ('followers', 'friends')
        except KeyError:
            raise ValueError('Must provide direction argument')
        except AssertionError:
            raise ValueError('Direction must be "followers" or "friends"')

        super(FollowJob, self).__init__(**kwargs)

        self.direction = direction

    def run(self):
        api_method = getattr(self.api, self.direction + '_ids')

        for target in self.targets:
            target.resolve(context=self, mode='fetch')

        users = it.chain(*[t.users for t in self.targets])

        n_items = 0
        for i, user in enumerate(users):
            msg = 'Processing user_id {0} ({1} / {2}), cumulative edges {3}'
            logger.info(msg.format(user.user_id, i + 1, len(users), n_items))

            ids = api_method(user_id=user.user_id)
            ids = ut.grouper(ids, self.load_batch_size)

            for j, batch in enumerate(ids):
                msg = 'Running {0} batch {1}, cumulative edges {2}'
                msg = msg.format(type(self), j + 1, n_items)
                logger.debug(msg)

                pass # FIXME

                if not self.onetxn:
                    self.session.commit()

                n_items += len(batch)

        if self.onetxn:
            self.session.commit()

