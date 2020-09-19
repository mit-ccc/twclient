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

        # make partial loads more statistically useful
        random.shuffle(self.targets)

        self._users = []
        self._bad_targets = []
        self._missing_targets = []
        if context is not None:
            self._context = context

    @abstractmethod
    def resolve(self, context, mode='fetch'):
        raise NotImplementedError()

    @property
    @abstractmethod
    def allowed_resolve_modes(self):
        raise NotImplementedError()

    @property
    def resolved(self):
        return hasattr(self, '_context')

    @property
    def users(self):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._users

    @property
    def bad_targets(self):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._bad_targets

    @property
    def missing_targets(self):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._missing_targets

    @property
    def context(self):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._context

    def _validate_context(self, context):
        if context.resolve_mode not in self.allowed_resolve_modes:
            raise ValueError('Bad operating mode for resolve()')

    def _mark_resolved(self, context):
        self._validate_context(context)
        self._context = context

    def _add_users(self, users):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        self._users.extend(users)

    def _add_bad_targets(self, targets):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        if not len(set(targets) - set(self.targets)) == 0:
            raise ValueError('All bad targets must be in self.targets')

        self._bad_targets.extend(targets)

    def _add_missing_targets(self, targets):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        if not len(set(targets) - set(self.targets)) == 0:
            raise ValueError('All missing targets must be in self.targets')

        self._missing_targets.extend(targets)

    def _tweepy_to_user(self, obj):
        user = md.User.from_tweepy(obj, self.context.session)
        self.context.session.merge(user)

        data = md.UserData.from_tweepy(obj, self.context.session)
        self.context.session.add(data)

        return user

    # splitting this out from _hydrate simplifies TwitterListTarget
    def _hydrate_only(self, user_ids=[], screen_names=[], **kwargs):
        try:
            assert (len(user_ids) > 0) ^ (len(screen_names) > 0)
        except AssertionError:
            raise ValueError('Must provide user_ids xor screen_names')

        kw = dict(kwargs, user_ids=user_ids, screen_names=screen_names)
        objs = [u for u in self.context.api.lookup_users(**kw)]

        users = [self._tweepy_to_user(u) for u in objs]

        # NOTE tweepy's lookup_users doesn't raise an exception on bad users, it
        # just doesn't return them, so we need to check the length of the input
        # and the number of user objects returned.
        if len(user_ids) > 0:
            requested = user_ids
            received = [u.user_id for u in objs]
        else: # len(screen_names) > 0
            requested = screen_names
            received = [u.screen_name.lower() for u in objs]

        bad_targets = list(set(requested) - set(received))

        return users, bad_targets

    def _hydrate(self, **kwargs):
        users, bad_targets = self._hydrate_only(**kwargs)

        self._add_users(users)
        self._add_bad_targets(bad_targets)

    def _user_for_screen_name(self, screen_name):
        return self.context.session.query(md.UserData).filter(
            func.lower(md.UserData.screen_name) == screen_name.lower()
        ).order_by(
            md.UserData.user_data_id.desc()
        ).first()

class UserIdTarget(Target):
    allowed_resolve_modes = ('fetch', 'hydrate', 'skip')

    def resolve(self, context):
        self._mark_resolved(context)

        if context.resolve_mode == 'hydrate':
            self._hydrate(user_ids=self.targets)
        else:
            existing = self.context.session.query(md.User) \
                           .filter(md.User.user_id.in_(self.targets))
            new = list(set(self.targets) - set([u.user_id for u in existing]))

            self._add_users(existing)
            self._add_missing_targets(new)

            if len(new) > 0:
                if context.resolve_mode == 'fetch':
                    self._hydrate(user_ids=new)
                else: # context.resolve_mode == 'skip'
                    logger.warning('Not all requested users are loaded')

class ScreenNameTarget(Target):
    allowed_resolve_modes = ('fetch', 'hydrate', 'skip')

    def resolve(self, context):
        self._mark_resolved(context)

        if context.resolve_mode == 'hydrate':
            self._hydrate(screen_names=self.targets)
        else:
            users = [self._user_for_screen_name(s) for s in self.targets]

            existing = [u for u in users if u is not None]
            new = [sn for u, sn in zip(users, self.targets) if u is None]

            self._add_users(existing)
            self._add_missing_targets(new)

            if len(new) > 0:
                if context.resolve_mode == 'fetch':
                    self._hydrate(screen_names=new)
                else: # context.resolve_mode == 'skip'
                    logger.warning('Not all requested users are loaded')

class SelectTagTarget(Target):
    allowed_resolve_modes = ('hydrate', 'skip')

    def resolve(self, context):
        self._mark_resolved(context)

        filters = [md.Tag.name == tag for tag in self.targets]
        tags = self.context.session.query(md.Tag).filter(or_(*filters)).all()
        new = list(set(self.targets) - set(tags))

        if len(new) > 0:
            msg = 'Requested tag(s) {0} do not exist'
            msg = msg.format(', '.join(new)
            logger.warning(msg)

        self._add_missing_targets(new)

        users = [user for tag in tags for user in tag.users]
        if context.resolve_mode == 'hydrate':
            self._hydrate(user_ids=[user.user_id for user in users])
        else: # context.resolve_mode == 'skip'
            self._add_users(users)

class TwitterListTarget(Target):
    allowed_resolve_modes = ('fetch', 'hydrate', 'skip')

    @property
    def owner_screen_names(self):
        return [obj.split('/')[0] for obj in self.targets]

    @property
    def slugs(self):
        return [obj.split('/')[1] for obj in self.targets]

    def _update_memberships(self, lst, members):
        ## Record user memberships in list
        new_uids = [u.user_id for u in members]
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
        for u in members:
            if u.user_id not in prev_uids:
                self.context.session.add(md.UserList(
                    list_id=lst.list_id,
                    user_id=u.user_id
                ))

    def _hydrate(self, lists):
        ## Hydrate the list owners
        # _hydrate_only doesn't raise NotFoundError on bad users because
        # lookup_users doesn't do so - no need to catch it
        owners, bad_owners = super(TwitterListTarget, self)._hydrate_only(
            screen_names=self.owner_screen_names
        )

        ## Get list info and list members
        for tg, owner, slug in zip(self.targets, owners, self.slugs):
            if owner in bad_owners:
                self._add_bad_targets([tg])
                continue

            try:
                kw = {'slug': slug, 'owner_id': owner.user_id}

                ## Fetch the list itself
                lst = self.context.api.get_list(**kw)
                lst = md.List.from_tweepy(lst, self.context.session)

                ## Fetch the list members from Twitter
                users = [u for u in self.context.api.list_members(**kw)]
            except err.NotFoundError as e:
                # the bad targets are logged in the calling Job class
                self._add_bad_targets([tg])
                continue
            else:
                lst = self.context.session.merge(lst)

                users = [self._tweepy_to_user(u) for u in users]
                self._add_users(users)

                self._update_memberships(lst, users)

    def resolve(self, context):
        self._mark_resolved(context)

        if context.resolve_mode == 'hydrate':
            self._hydrate(self.targets)

        new = []
        for tg, sn, slug in zip(self.targets, self.owner_screen_names, self.slugs):
            owner = self._user_for_screen_name(sn)

            if owner is None: # list hasn't been ingested
                self._add_missing_targets([tg])

                if context.resolve_mode == 'fetch':
                    new += [tg]
                else: # context.resolve_mode == 'skip'
                    continue

            lst = self.context.session.query(md.List).filter(and_(
                md.List.user_id == owner.user_id,
                md.List.slug == slug
            )).one_or_none()

            if lst is None: # list hasn't been ingested
                self._add_missing_targets([tg])

                if context.resolve_mode == 'fetch':
                    new += [tg]
                else: # context.resolve_mode == 'skip'
                    continue

            # every user currently recorded as a list member
            users = self.context.session.query(md.User).filter(
                md.User.user_id.in_([
                    m.user_id
                    for m in lst.list_memberships
                    if m.valid_end_dt is None # as above
                ])
            )

            self._add_users(users)

        if context.resolve_mode == 'fetch' and len(new) > 0:
            self._hydrate(new)

