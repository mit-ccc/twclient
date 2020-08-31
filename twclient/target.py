# FIXME may need to think through new_only some more - is this a full replacement
# for new in sync_users?

import random

import twclient.models as md

from abc import ABC, abstractmethod
from sqlalchemy import exists, or_, and_

class Target(ABC):
    def __init__(self, **kwargs):
        try:
            targets = kwargs.pop('targets')
        except KeyError:
            raise ValueError('Must specify targets')

        super(Target, self).__init__(**kwargs)

        targets = list(set(targets))
        random.shuffle(targets) # make partial loads more statistically useful
        self.targets = targets

    # rehydrate means require a refetch from the Twitter API even where we
    # already did so >= 1 time before and have the data. new_only, which is a
    # property of the set of targets rather than how to fetch them, means
    # exclude any user we already have in the DB
    @abstractmethod
    def to_user_objects(self, session, api, mode='fetch'):
        raise NotImplementedError()

class UserIdTarget(Target):
    def to_user_objects(self, session, api, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for to_user_objects')

        if mode == 'rehydrate':
            objs = api.lookup_users(user_ids=self.targets)
            yield from (md.User.from_tweepy(obj) for obj in objs)
        else:
            presents = session.query(md.User).filter(md.User.user_id.in_(self.targets))
            yield from presents

            if mode == 'fetch':
                missings = list(set(self.targets) - set([x.user_id for x in presents]))
                objs = api.lookup_users(user_ids=missings)
                yield from (md.User.from_tweepy(obj) for obj in objs)

class SelectTagTarget(Target):
    def to_user_objects(self, session, api, mode='fetch'):
        # fetch doesn't make sense here: tag isn't a twitter entity
        if mode not in ('rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for to_user_objects')

        filters = [md.Tag.name == tag for tag in self.targets]
        tags = session.query(md.Tag).filter(or_(*filters))

        if mode != 'skip_missing' and len(tags) < len(self.targets):
            raise ValueError("Not all provided tags exist")

        users = [user for tag in tags for user in tag.users]

        if mode == 'rehydrate':
            user_ids = [user.user_id for user in users]
            objs = api.lookup_users(user_ids=user_ids)

            yield from (md.User.from_tweepy(obj) for obj in objs)
        else:
            yield from users

class ScreenNameTarget(Target):
    def to_user_objects(self, session, api, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for to_user_objects')

        if mode == 'rehydrate':
            objs = api.lookup_users(screen_names=self.targets)
            yield from (md.User.from_tweepy(obj) for obj in objs)
        else:
            # NOTE screen_name is assumed to be unique in md.User
            presents = session.query(md.User).filter(md.User.screen_name.in_(self.targets))
            yield from presents

            if mode == 'fetch':
                missings = list(set(self.targets) - set([x.screen_name for x in presents]))
                objs = api.lookup_users(screen_names=missings)
                yield from (md.User.from_tweepy(obj) for obj in objs)

class TwitterListTarget(Target):
    def to_user_objects(self, session, api, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for to_user_objects')

        if rehydrate:
            pass
        else:
            pass

