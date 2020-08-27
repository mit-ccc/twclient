# FIXME what about new?

import models as md

from abc import ABC, abstractmethod

from sqlalchemy import exists

class Target(ABC):
    def __init__(self, **kwargs):
        try:
            targets = kwargs.pop('targets')
        except KeyError:
            raise ValueError('Must specify targets')

        super(Target, self).__init__(**kwargs)

        self.targets = list(set(targets))

        # Make partial loads more statistically useful
        random.shuffle(self.targets)

    @abstractmethod
    def user_objects(self, api=None):
        raise NotImplementedError()

class ApiAwareMixin(object):
    def __init__(self, **kwargs):
        try:
            api = kwargs.pop('api')
        except KeyError:
            raise ValueError('Must specify api')

        super(ApiAwareMixin, self).__init__(**kwargs)

        self.api = api

    def user_objects_for(self, objs, kind):
        logger.debug('Fetching user objects for {0}'.format(kind))

        assert kind in ('user_ids', 'screen_names', 'twitter_lists')

        if kind == 'twitter_lists':
            for i, obj in enumerate(objs):
                logger.info('Running list {1}: {2}'.format(i, obj))

                owner_screen_name, slug = obj.split('/')

                yield from self.api.make_api_call(
                    method='list_members',
                    cursor=True,
                    slug=slug,
                    owner_screen_name=owner_screen_name
                )
        else:
            for i, grp in enumerate(ut.grouper(objs, 100)): # max 100 per call
                logger.info('Running {0} batch {1}'.format(kind, i))

                yield from self.api.make_api_call(
                    method='lookup_users',
                    **{kind: grp}
                )

    def user_objects_for_lists(self, twitter_lists):
        yield from self.user_objects_for(twitter_lists, kind='twitter_lists')

    def user_objects_for_ids(self, user_ids, new=False):
        if not new:
            objs = user_ids
        else:
            objs = (
                user_id
                for user_id in user_ids
                if not self.user_id_exists(user_id)
            )
        yield from self.user_objects_for(objs=objs, kind='user_ids')

    def user_objects_for_screen_names(self, screen_names, new=False):
        if not new:
            objs = screen_names
        else:
            objs = (
                screen_name
                for screen_name in screen_names
                if self.user_id_for_screen_name(screen_name) is None
            )

        yield from self.user_objects_for(objs=objs, kind='screen_names')

class ScreenNameTarget(Target):
    def user_objects(self, api):

class ListTarget(Target):
    def user_objects(self, api):
        yield from (
            md.User.from_tweepy(u)
            for lst in self.targets
            for u in api.list_members(lst)
        )

class SelectTagTarget(Target):
    def __init__(

class UserIdTarget(Target):
    def user_objects(self, api=None):

