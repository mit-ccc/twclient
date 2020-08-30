# FIXME may need to think through new_only some more - is this a full replacement
# for new in sync_users?

import twclient.models as md
import twclient.twitter_api as ta

from abc import ABC, abstractmethod
from sqlalchemy import exists

class Target(ABC):
    def __init__(self, **kwargs):
        try:
            targets = kwargs.pop('targets')
        except KeyError:
            raise ValueError('Must specify targets')

        new_only = kwargs.pop('new_only', False)

        super(Target, self).__init__(**kwargs)

        targets = list(set(targets))
        random.shuffle(targets) # make partial loads more statistically useful

        self.targets = targets
        self.new_only = new_only

    # rehydrate means require a refetch from the Twitter API even where we
    # already did so >= 1 time before and have the data. new_only, which is a
    # property of the set of targets rather than how to fetch them, means
    # exclude any user we already have in the DB
    @abstractmethod
    def to_user_objects(self, api, session, rehydrate=True):
        raise NotImplementedError()

class UserIdTarget(Target):
    def user_objects(self, api, session, rehydrate=True):
        pass

class ScreenNameTarget(Target):
    def to_user_objects(self, api, session, rehydrate=True):
        pass

class ListTarget(Target):
    def to_user_objects(self, api, session, rehydrate=True):
        pass

class SelectTagTarget(Target):
    def user_objects(self, api, session, rehydrate=True):
        pass

# def user_objects_for(self, objs, kind):
#     logger.debug('Fetching user objects for {0}'.format(kind))
#
#     assert kind in ('user_ids', 'screen_names', 'twitter_lists')
#
#     if kind == 'twitter_lists':
#         for i, obj in enumerate(objs):
#             logger.info('Running list {1}: {2}'.format(i, obj))
#
#             owner_screen_name, slug = obj.split('/')
#
#             yield from self.api.make_api_call(
#                 method='list_members',
#                 cursor=True,
#                 slug=slug,
#                 owner_screen_name=owner_screen_name
#             )
#     else:
#         for i, grp in enumerate(ut.grouper(objs, 100)): # max 100 per call
#             logger.info('Running {0} batch {1}'.format(kind, i))
#
#             yield from self.api.make_api_call(
#                 method='lookup_users',
#                 **{kind: grp}
#             )
#
# def user_objects_for_lists(self, twitter_lists):
#     yield from self.user_objects_for(twitter_lists, kind='twitter_lists')
#
# def user_objects_for_ids(self, user_ids, new=False):
#     if not new:
#         objs = user_ids
#     else:
#         objs = (
#             user_id
#             for user_id in user_ids
#             if not self.user_id_exists(user_id)
#         )
#     yield from self.user_objects_for(objs=objs, kind='user_ids')
#
# def user_objects_for_screen_names(self, screen_names, new=False):
#     if not new:
#         objs = screen_names
#     else:
#         objs = (
#             screen_name
#             for screen_name in screen_names
#             if self.user_id_for_screen_name(screen_name) is None
#         )
#
#     yield from self.user_objects_for(objs=objs, kind='screen_names')

