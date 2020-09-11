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
        n_items = 0
        for target in self.targets:
            target.resolve(context=self, mode='fetch')

            for user in target.users:
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

                for i, batch in enumerate(tweets):
                    msg = 'Running {0} batch {1}, cumulative objects {2}'
                    msg = msg.format(type(self), i + 1, n_items)
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
        direction = kwargs.pop('direction', 'followers')

        super(FollowJob, self).__init__(**kwargs)

        assert direction in ('followers', 'friends')
        self.direction = direction

    def run(self):
        self.sync_users(targets=self.targets, target_type=self.target_type,
                        new=True, full=self.full, commit=(not self.onetxn))

        if self.target_type == 'user_ids':
            user_ids = self.targets
        if self.target_type == 'screen_names':
            user_ids = self.user_ids_for_screen_names(self.targets)

        # there may be very very many users returned, so let's process
        # them incrementally rather than building one giant list
        n_items = 0
        for i, (user_id, target) in enumerate(zip(user_ids, self.targets)):
            if user_id is None and self.target_type == 'screen_names':
                msg = 'Skipping unknown screen name {0}'.format(target)
                logger.warning(msg)

                continue

            msg = 'Processing user {0} ({1} / {2})'
            logger.debug(msg.format(user_id, i + 1, len(user_ids)))

            ff_id = self.load_follow_fetch(user_id=user_id,
                                           direction=self.direction)

            edges = self.follow_objects_for(objs=[user_id], kind='user_ids',
                                            direction=self.direction)
            edges = ut.grouper(edges, self.load_batch_size)

            for j, batch in enumerate(edges):
                msg = 'Running user {0} ({1}/{2}) batch {3}, ' \
                      'cumulative edges {4}'
                msg = msg.format(user_id, i + 1, len(user_ids), j + 1, n_items)
                logger.info(msg)

                self.load_follow_edges(edges=batch, follow_fetch_id=ff_id)
                n_items += len(batch)

            # NOTE: it's safe to commit here even if make_api_call caught a
            # BadUserError, because in that case it just won't return any rows
            # and the loop above is a no-op
            if not self.onetxn:
                self.commit()

        if self.onetxn:
            self.commit()

    @staticmethod
    def follow_edges(api, direction, user_ids):
        try:
            assert direction in ('followers', 'friends')
        except AssertionError:
            raise ValueError('Bad direction for follow edge fetch')

        method = getattr(api, direction + '_ids')

        for obj in user_ids:
            edges = method(user_id=obj)

            for item in edges:
                if direction == 'followers':
                    yield {'source': item, 'target': obj}
                else: # direction == 'friends'
                    yield {'source': obj, 'target': item}

