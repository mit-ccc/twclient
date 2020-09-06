import random
import logging
import itertools as it

from abc import ABC, abstractmethod

from sqlalchemy.orm import sessionmaker

import tweepy

import twclient.error as err
import twclient.utils as ut
import twclient.models as md
import twclient.twitter_api as ta

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

    def batchify(self, objects, func, **kwargs):
        n_items = 0
        for i, batch in enumerate(ut.grouper(objects, self.load_batch_size)):
            msg = 'Running {0} batch {1}, cumulative objects {2}'
            msg = msg.format(type(self), i + 1, n_items)
            logger.debug(msg)

            n_items += len(batch)

            func(batch, **kwargs)

            if not self.onetxn:
                self.session.commit()

        if self.onetxn:
            self.session.commit()

    @abstractmethod
    def run(self):
        raise NotImplementedError()

class UserInfoJob(Job):
    def run(self):
        if self.user_tag is not None:
            tag = self.get_or_create(md.Tag, name=self.user_tag)

        for target in self.targets:
            # also merges user objects into self.session
            users = target.to_user_objects(context=self, mode='rehydrate')

            for user in users:
                if self.user_tag is not None:
                    user.tags.append(tag)

                self.session.add(user)

        self.session.commit()

class TweetsJob(Job):
    def __init__(self, **kwargs):
        since_timestamp = kwargs.pop('since_timestamp', None)
        max_tweets = kwargs.pop('max_tweets', None)
        old_tweets = kwargs.pop('old_tweets', False)
        tweet_tag = kwargs.pop('tweet_tag', None)
        full = kwargs.pop('full', False)

        super(TweetsJob, self).__init__(**kwargs)

        # NOTE this could be implemented but has not been
        if self.target_type == 'twitter_lists':
            raise NotImplementedError()

        self.since_timestamp = since_timestamp
        self.max_tweets = max_tweets
        self.old_tweets = old_tweets
        self.tweet_tag = tweet_tag
        self.full = full

    def run(self):
        self.sync_users(targets=self.targets, target_type=self.target_type,
                        new=True, full=self.full, commit=(not self.onetxn))

        if self.target_type == 'user_ids':
            user_ids = self.targets
        if self.target_type == 'screen_names':
            user_ids = self.user_ids_for_screen_names(self.targets)

        if self.old_tweets:
            logger.debug('Allowing old tweets')
            since_ids = [None for x in user_ids]
        else:
            logger.debug('Skipping old tweets')
            since_ids = self.max_tweet_ids_for_user_ids(user_ids)

        n_items = 0
        for i, (user_id, since_id, target) in enumerate(zip(user_ids, since_ids,
                                                            self.targets)):
            if user_id is None and self.target_type == 'screen_names':
                msg = 'Skipping unknown screen name {0}'.format(target)
                logger.warning(msg)

                continue

            msg = 'Processing user {0} ({1} / {2})'
            logger.debug(msg.format(user_id, i + 1, len(user_ids)))

            tweets = self.tweet_objects_for_ids(**{
                'user_ids': [user_id],
                'since_ids': [since_id],
                'max_tweets': self.max_tweets,
                'since_timestamp': self.since_timestamp
            })

            for j, batch in enumerate(ut.grouper(tweets, self.load_batch_size)):
                msg = 'Running user {0} ({1} / {2}) batch {3}, ' \
                      'cumulative tweets {4}'
                msg = msg.format(user_id, i + 1, len(user_ids), j + 1, n_items)
                logger.info(msg)

                self.load_tweets(batch, load_mentions=True)
                n_items += len(batch)

            # NOTE: it's safe to commit here even if make_api_call caught a
            # BadUserError, because in that case it just won't return any rows
            # and the loop above is a no-op
            if not self.onetxn:
                self.commit()

        if self.onetxn:
            self.commit()

class FollowJob(Job):
    def __init__(self, **kwargs):
        direction = kwargs.pop('direction', 'followers')
        full = kwargs.pop('full', False)

        assert full is not None
        assert direction in ('followers', 'friends')

        super(FollowJob, self).__init__(**kwargs)

        assert self.target_type != 'twitter_lists'

        self.direction = direction
        self.full = full

    # What we're doing here:
    # 1) load user to twitter.user if not already there
    # 2) load the follow_fetch row, get its id, ff_id
    # 3) loop over pages of graph neighbors:
        # 3a) get the users from twitter
        # 3b) if requested, hydrate the users via users/lookup
        # 3c) load the users to twitter.user, merging if present
        # 3d) load the follow rows to twitter.follow, using ff_id
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

    # def load_mentions(self, tweets):
    #     logger.debug('Loading mentions')

    #     mentions, mentioned_users = self.mentions_for_tweets(tweets)
    #     mentioned_ids = list(set([x['user_id'] for x in mentioned_users]))

    #     self.sync_users(targets=mentioned_ids, target_type='user_ids',
    #                     full=self.full, new=True, commit=False)

    #     self.db_load_data(
    #         data=Rowset.from_records(MentionRow, mentions),
    #         conflict='merge',
    #         conflict_constraint=['tweet_id', 'mentioned_user_id']
    #     )

    # def load_tweets(self, tweets, load_mentions=True):
    #     logger.debug('Loading tweets')

    #     tweets = [t for t in tweets] # no generators, need >1 reference

    #     rows = [TweetRow.from_tweepy(u) for u in tweets]
    #     tweet_ids = [t.as_record()['tweet_id'] for t in rows]
    #     twrows = Rowset(rows=rows, cls=TweetRow)

    #     self.db_load_data(twrows, conflict='merge',
    #                       conflict_constraint=['tweet_id'])

    #     if self.tweet_tag is not None:
    #         ttrows = Rowset(rows=(
    #             TweetTagRow(tweet_id=t, tag=self.tweet_tag)
    #             for t in tweet_ids
    #         ), cls=TweetTagRow)

    #         self.db_load_data(ttrows, conflict='merge',
    #                           conflict_constraint=['user_id', 'tag'])

    #     if load_mentions:
    #         self.load_mentions(tweets)

    # # edges are assumed to be (source, target)
    # def load_follow_edges(self, edges, follow_fetch_id):
    #     logger.debug('Loading follow edges')

    #     edges = [e for e in edges]

    #     user_ids = list(set([x for y in edges for x in y]))
    #     self.sync_users(targets=user_ids, target_type='user_ids',
    #                     full=self.full, new=True, commit=False)

    #     rows = Rowset(rows=(
    #         FollowRow(
    #             follow_fetch_id=follow_fetch_id,
    #             source_user_id=source,
    #             target_user_id=target
    #         ) for source, target in edges
    #     ), cls=FollowRow)

    #     cols = ['follow_fetch_id', 'source_user_id', 'target_user_id']
    #     self.db_load_data(rows, conflict='merge', conflict_constraint=cols)

    # ## Most API methods will encounter and need to handle new user
    # ## objects, not just the jobs that only load user info
    # def load_users(self, targets, kind):
    #     logger.debug('Loading {0} users'.format(kind))

    #     assert kind in ('users', 'user_ids')

    #     if kind == 'users':
    #         rows = [UserRow.from_tweepy(u) for u in targets]
    #     else:
    #         rows = [UserRow(user_id=u) for u in targets]

    #     user_ids = [u.as_record()['user_id'] for u in rows]

    #     urows = Rowset(rows=rows, cls=UserRow)
    #     self.db_load_data(urows, conflict='merge',
    #                       conflict_constraint=['user_id'])

    #     if self.user_tag is not None:
    #         logger.debug('Loading user tags: {0}'.format(self.user_tag))

    #         tag_rows = Rowset(rows=(
    #             UserTagRow(tag=self.user_tag, user_id=u)
    #             for u in user_ids
    #         ), cls=UserTagRow)

    #         self.db_load_data(tag_rows, conflict='merge',
    #                           conflict_constraint=['user_id', 'tag'])

    # # Given a set of targets, which may be screen names, user ids or
    # # users in a Twitter list and which may not exist in the twitter.user
    # # table yet, we want to a) resolve them all to user ids
    # # and b) ensure they all exist in the twitter.user table.
    # def sync_users(self, targets, target_type, new=True, full=False,
    #                commit=False):
    #     msg = 'Syncing {0} users, new={1}, full={2}, commit={3}'
    #     logger.debug(msg.format(target_type, new, full, commit))

    #     # full doesn't matter in the first two cases: we have to fetch
    #     # every user from the twitter API anyway because all we have
    #     # is a screen name
    #     if target_type == 'twitter_lists':
    #         # "new" is ignored here: we have to fetch them all from the
    #         # list members endpoint anyway to even learn who they are
    #         kind = 'users'
    #         users = self.user_objects_for_lists(self.targets)
    #     elif target_type == 'screen_names':
    #         kind = 'users'
    #         users = self.user_objects_for_screen_names(targets, new=new)
    #     elif full:
    #         kind = 'users'
    #         users = self.user_objects_for_ids(targets, new=new)
    #     else:
    #         kind = 'user_ids'
    #         users = targets

    #     n_items = 0
    #     for i, batch in enumerate(ut.grouper(users, self.load_batch_size)):
    #         msg = 'Running user batch {0}, cumulative users {1}'
    #         msg = msg.format(i + 1, n_items)
    #         logger.debug(msg)

    #         self.load_users(targets=batch, kind=kind)

    #         n_items += len(batch)

    #         if commit:
    #             self.commit()

