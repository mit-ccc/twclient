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

    @abstractmethod
    def to_user_objects(self, context, mode='fetch'):
        raise NotImplementedError()

class UserIdTarget(Target):
    def to_user_objects(self, context, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for to_user_objects')

        if mode == 'rehydrate':
            for obj in context.api.lookup_users(user_ids=self.targets):
                yield context.session.merge(md.User.from_tweepy(obj))
        else:
            existing = context.session.query(md.User) \
                            .filter(md.User.user_id.in_(self.targets))
            new = list(set(self.targets) - set([u.user_id for u in existing]))

            yield from existing

            if mode == 'fetch':
                for obj in context.api.lookup_users(user_ids=new):
                    yield context.session.merge(md.User.from_tweepy(obj))

class ScreenNameTarget(Target):
    def to_user_objects(self, context, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for to_user_objects')

        # NOTE screen_name is assumed to be unique in md.User
        if mode == 'rehydrate':
            for obj in context.api.lookup_users(screen_names=self.targets):
                yield context.session.merge(md.User.from_tweepy(obj))
        else:
            existing = context.session.query(md.User) \
                              .filter(md.User.screen_name.in_(self.targets))
            new = list(set(self.targets) - set([u.screen_name for u in existing]))

            yield from existing

            if mode == 'fetch':
                for obj in context.api.lookup_users(screen_names=new):
                    yield context.session.merge(md.User.from_tweepy(obj))

class SelectTagTarget(Target):
    def to_user_objects(self, context, mode='fetch'):
        # fetch doesn't make sense here: tag isn't a twitter entity
        if mode not in ('rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for to_user_objects')

        filters = [md.Tag.name == tag for tag in self.targets]
        tags = context.session.query(md.Tag).filter(or_(*filters)).all()

        if mode != 'skip_missing' and len(tags) < len(self.targets):
            raise ValueError("Not all provided tags exist")

        users = [user for tag in tags for user in tag.users]

        if mode == 'rehydrate':
            user_ids = [user.user_id for user in users]
            for obj in context.api.lookup_users(user_ids=user_ids):
                yield context.session.merge(md.User.from_tweepy(obj))
        else:
            yield from users

class TwitterListTarget(Target):
    def to_user_objects(self, context, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for to_user_objects')

        owner_screen_names = [obj.split('/')[0] for obj in self.targets]
        slugs = [obj.split('/')[1] for obj in self.targets]

        if mode == 'rehydrate':
            ## First, refresh the owning users - we don't yield these
            owning_users = [
                context.session.merge(md.User.from_tweepy(obj))
                for obj in context.api.lookup_users(screen_names=owner_screen_names)
            ]

            ## Second, refresh the list objects - we don't yield these either
            for owner, slug in zip(owning_users, slugs):
                lst = context.api.get_list(slug=slug, owner_id=owner.user_id)
                context.session.merge(md.List.from_tweepy(lst))

            ## Third, refresh the users in the list
            objs = it.chain(*[
                context.api.list_members(slug=slug, owner_id=owner.user_id)
                for owner, slug in zip(owning_users, slugs)
            ])

            for obj in objs:
                yield context.session.merge(md.User.from_tweepy(obj))
        else:
            pass
            # exist_owners = context.session.query(md.User) \
            #                       .filter(screen_name.in_(owner_screen_names))
            # miss_owners = list(set(

