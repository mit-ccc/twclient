import random
import itertools as it

from . import models as md

from abc import ABC, abstractmethod
from sqlalchemy import exists, or_, and_, func

class Target(ABC):
    def __init__(self, **kwargs):
        try:
            targets = kwargs.pop('targets')
        except KeyError:
            raise ValueError('Must specify targets')

        context = kwargs.pop('context', None)

        super(Target, self).__init__(**kwargs)

        self.targets = list(set(targets))

        if context is not None:
            self._context = context

        # make partial loads more statistically useful
        random.shuffle(self.targets)

    @property
    def resolved(self):
        return all([
            hasattr(self, '_users'),
            hasattr(self, '_context')
        ])

    @property
    def users(self):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._users

    @property
    def context(self):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._context

    def tweepy_to_user(self, obj):
        user = md.User.from_tweepy(obj)
        self.context.session.merge(user)

        data = md.UserData.from_tweepy(obj)
        self.context.session.add(data)

        return user

    def hydrate(self, **kwargs):
        for obj in self.context.api.lookup_users(**kwargs):
            yield self.tweepy_to_user(obj)

    def user_for_screen_name(self, screen_name):
        return self.context.session.query(md.UserData).filter(
            func.lower(md.UserData.screen_name) == screen_name.lower()
        ).order_by(
            md.UserData.user_data_id.desc()
        ).first().user

    @abstractmethod
    def resolve(self, context, mode='fetch'):
        raise NotImplementedError()

class UserIdTarget(Target):
    def resolve(self, context, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for resolve')

        self._users = []
        self._context = context

        if mode == 'rehydrate':
            self._users.extend(self.hydrate(user_ids=self.targets))
        else:
            existing = self.context.session.query(md.User) \
                           .filter(md.User.user_id.in_(self.targets))
            new = list(set(self.targets) - set([u.user_id for u in existing]))

            self._users.extend(existing)
            if mode == 'fetch':
                self._users.extend(self.hydrate(user_ids=new))

class ScreenNameTarget(Target):
    def resolve(self, context, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for resolve')

        self._users = []
        self._context = context

        if mode == 'rehydrate':
            self._users.extend(self.hydrate(screen_names=self.targets))
        else:
            users = [self.user_for_screen_name(s) for s in self.targets]

            existing = [u for u in users if u is not None]
            new = [sn for u, sn in zip(users, self.targets) if u is None]

            self._users.extend(existing)

            if mode == 'fetch':
                self._users.extend(self.hydrate(screen_names=new))

class SelectTagTarget(Target):
    def resolve(self, context, mode='fetch'):
        if mode not in ('existing', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for resolve')

        self._users = []
        self._context = context

        filters = [md.Tag.name == tag for tag in self.targets]
        tags = self.context.session.query(md.Tag).filter(or_(*filters)).all()

        if mode != 'skip_missing' and len(tags) < len(self.targets):
            raise ValueError("Not all provided tags exist")

        users = [user for tag in tags for user in tag.users]
        if mode == 'rehydrate':
            users = self.hydrate(user_ids=[user.user_id for user in users])

        self._users.extend(users)

class TwitterListTarget(Target):
    def resolve(self, context, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip_missing'):
            raise ValueError('Bad mode for resolve')

        self._users = []
        self._context = context

        owner_screen_names = [obj.split('/')[0] for obj in self.targets]
        slugs = [obj.split('/')[1] for obj in self.targets]

        if mode == 'rehydrate':
            ## Hydrate the list owners
            owners = self.hydrate(screen_names=owner_screen_names)

            for owner, slug in zip(owners, slugs):
                ## Fetch the list and its existing memberships
                lst = self.context.session.merge(md.List.from_tweepy(
                    self.context.api.get_list(
                        slug=slug,
                        owner_id=owner.user_id
                    )
                ))

                ## Fetch the list members from Twitter
                users = [
                    self.tweepy_to_user(obj)

                    for obj in self.context.api.list_members(
                        slug=slug,
                        owner_id=owner.user_id
                    )
                ]

                self._users.extend(users)

                ## Record user memberships in list
                current_uids = [u.user_id for u in users]
                prev_uids = [m.user_id for m in lst.list_memberships]

                for m in lst.list_memberships:
                    if m.user_id not in current_uids:
                        m.valid_end_dt = func.now()

                for u in users:
                    if u.user_id not in prev_uids:
                        self.context.session.add(md.UserList(
                            list_id=lst.list_id,
                            user_id=u.user_id
                        ))
        else:
            owners = [
                self.user_for_screen_name(sn)
                for sn in owner_screen_names
            ]

            flts = []
            lists = self.context.session.query(md.List).filter(or_(*flts)).all()


