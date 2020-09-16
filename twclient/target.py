import random
import logging
import itertools as it

from . import models as md

from abc import ABC, abstractmethod
from sqlalchemy import exists, or_, and_, func

from . import error as err

logger = logging.getLogger(__name__)

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

    @abstractmethod
    def resolve(self, context, mode='fetch'):
        raise NotImplementedError()

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

    def _mark_resolved(self, context):
        self._users = []
        self._context = context

    def _add_users(self, users):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        self._users.extend(users)

    def _tweepy_to_user(self, obj):
        user = md.User.from_tweepy(obj)
        self.context.session.merge(user)

        data = md.UserData.from_tweepy(obj)
        self.context.session.add(data)

        return user

    def _hydrate(self, **kwargs):
        users = [
            self._tweepy_to_user(obj)
            for obj in self.context.api.lookup_users(**kwargs)
        ]

        self._add_users(users)

        return users

    def _user_for_screen_name(self, screen_name):
        ret = self.context.session.query(md.UserData).filter(
            func.lower(md.UserData.screen_name) == screen_name.lower()
        ).order_by(
            md.UserData.user_data_id.desc()
        ).first()

        if ret:
            return ret.user
        else:
            msg = 'Screen name {0} not found locally or does not exist; ' \
                  'use hydrate?'
            raise err.BadTargetError(message=msg.format(screen_name))

class UserIdTarget(Target):
    def resolve(self, context, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip', 'raise'):
            raise ValueError('Bad mode for resolve')

        self._mark_resolved(context)

        if mode == 'rehydrate':
            self._hydrate(user_ids=self.targets)
        else:
            existing = self.context.session.query(md.User) \
                           .filter(md.User.user_id.in_(self.targets))
            new = list(set(self.targets) - set([u.user_id for u in existing]))

            if len(new) > 0:
                if mode == 'fetch':
                    self._hydrate(user_ids=new)
                elif mode == 'raise':
                    msg = 'Not all requested users are loaded'
                    raise err.BadTargetError(message=msg)
                else: # mode == 'skip'
                    logger.warning('Not all requested users are loaded')

            self._add_users(existing)

class ScreenNameTarget(Target):
    def resolve(self, context, mode='fetch'):
        if mode not in ('fetch', 'rehydrate', 'skip', 'raise'):
            raise ValueError('Bad mode for resolve')

        self._mark_resolved(context)

        if mode == 'rehydrate':
            self._hydrate(screen_names=self.targets)
        else:
            users = [self._user_for_screen_name(s) for s in self.targets]

            existing = [u for u in users if u is not None]
            new = [sn for u, sn in zip(users, self.targets) if u is None]

            if len(new) > 0:
                if mode == 'fetch':
                    self._hydrate(screen_names=new)
                elif mode == 'raise':
                    msg = 'Not all requested users are loaded'
                    raise err.BadTargetError(message=msg)
                else: # mode == 'skip'
                    logger.warning('Not all requested users are loaded')

            self._add_users(existing)

class SelectTagTarget(Target):
    def resolve(self, context, mode='existing'):
        if mode not in ('rehydrate', 'skip', 'raise'):
            raise ValueError('Bad mode for resolve')

        self._mark_resolved(context)

        filters = [md.Tag.name == tag for tag in self.targets]
        tags = self.context.session.query(md.Tag).filter(or_(*filters)).all()

        if len(tags) < len(self.targets):
            if mode == 'raise':
                msg = 'Not all requested tags exist'
                raise err.BadTargetError(message=msg)
            else: # mode == 'skip'
                logger.warning('Not all requested tags exist')

        users = [user for tag in tags for user in tag.users]
        if mode == 'rehydrate':
            self._hydrate(user_ids=[user.user_id for user in users])
        else:
            self._add_users(users)

class TwitterListTarget(Target):
    def _hydrate_lists(self, lists):
        owner_screen_names = [obj.split('/')[0] for obj in lists]
        slugs = [obj.split('/')[1] for obj in lists]

        ## Hydrate the list owners
        owners = self._hydrate(screen_names=owner_screen_names)

        for owner, slug in zip(owners, slugs):
            ## Fetch the list and its existing memberships
            lst = self.context.session.merge(md.List.from_tweepy(
                # FIXME what happens if the list dne?
                self.context.api.get_list(
                    slug=slug,
                    owner_id=owner.user_id
                )
            ))

            ## Fetch the list members from Twitter
            users = [
                self._tweepy_to_user(obj)

                for obj in self.context.api.list_members(
                    slug=slug,
                    owner_id=owner.user_id
                )
            ]

            self._add_users(users)

            ## Record user memberships in list
            new_uids = [u.user_id for u in users]
            prev_uids = [
                m.user_id
                for m in lst.list_memberships
                if m.valid_end_dt is None # SCD type 2's currently valid rows
            ]

            # mark rows no longer in Twitter API's list as invalid
            for m in lst.list_memberships:
                if m.user_id not in new_uids:
                    m.valid_end_dt = func.now()

            # add rows for users newly present in Twitter API's list
            for u in users:
                if u.user_id not in prev_uids:
                    self.context.session.add(md.UserList(
                        list_id=lst.list_id,
                        user_id=u.user_id
                    ))

    def resolve(self, context, mode='fetch'):
        # FIXME make modes work right
        if mode not in ('fetch', 'rehydrate', 'skip', 'raise'):
            raise ValueError('Bad mode for resolve')

        self._mark_resolved(context)

        if mode == 'rehydrate':
            self._hydrate_lists(self.targets)
        else:
            owner_screen_names = [obj.split('/')[0] for obj in self.targets]
            slugs = [obj.split('/')[1] for obj in self.targets]

            new = []
            for tg, sn, slug in zip(self.targets, owner_screen_names, slugs):
                owner = self._user_for_screen_name(sn)

                if owner is None: # list hasn't been ingested
                    if mode == 'fetch':
                        new += [tg]
                    elif mode == 'raise':
                        msg = 'List owner {0} is not loaded or does not exist'
                        raise err.BadTargetError(message=msg.format(sn))
                    else: # mode == 'skip'
                        continue

                lst = self.context.session.query(md.List).filter(and_(
                    md.List.user_id == owner.user_id,
                    md.List.slug == slug
                )).one()

                # every user currently recorded as a list member
                users = self.context.session.query(md.User).filter(
                    md.User.user_id.in_([
                        m.user_id
                        for m in lst.list_memberships
                        if m.valid_end_dt is None # as above
                    ])
                )

                self._add_users(users)

            if mode == 'fetch' and len(new) > 0:
                self._hydrate_lists(new)
