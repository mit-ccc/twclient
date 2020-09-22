import logging

import tweepy

from . import error as err
from . import utils as ut
from . import authpool as ap

logger = logging.getLogger(__name__)

def to_user_type(user_id, screen_name):
    try:
        assert user_id is not None or screen_name is not None
        assert user_id is None or screen_name is None
    except AssertionError:
        raise ValueError("Must provide user_id xor screen_name")

    user_type = 'user_id' if user_id is not None else 'screen_name'
    user = ut.coalesce(user_id, screen_name)

    return user, user_type

class TwitterApi(object):
    def __init__(self, **kwargs):
        try:
            auths = kwargs.pop('auths')
        except KeyError:
            raise ValueError('auths argument is required')

        super(TwitterApi, self).__init__(**kwargs)

        self.auths = auths
        self.pool = ap.AuthPoolAPI(auths=auths)

    def make_api_call(self, method, cursor=False, max_items=None, **kwargs):
        msg = 'API call: {0} with params {1}, cursor {2}'
        logger.debug(msg.format(method, kwargs, cursor))

        func = getattr(self.pool, method)
        return_type = getattr(func, 'twclient_return_type')

        try:
            assert not (cursor and max_items is not None)
        except AssertionError:
            raise ValueError("max_items only available with cursor=True")

        twargs = dict({'method': func}, **kwargs)

        try:
            if cursor and max_items is not None:
                ret = tweepy.Cursor(**twargs).items(max_items)
            elif cursor:
                ret = tweepy.Cursor(**twargs).items()
            else:
                ret = func(**kwargs)

            if return_type == 'single':
                yield ret
            elif return_type == 'list':
                yield from ret
            else: # return_type == 'unknown'
                msg = 'Return type of method {0} unspecified'.format(name)
                raise RuntimeError(msg)
        except Exception as e:
            msg = 'Exception in call to Twitter API: {0}'.format(repr(e))
            logger.debug(msg, exc_info=True)

            raise

    ##
    ## Direct wraps of Twitter API methods
    ##

    def lookup_users(self, user_ids=[], screen_names=[], **kwargs):
        msg = 'Hydrating user_ids {0} and screen_names {1}'
        logger.debug(msg.format(user_ids, screen_names))

        try:
            assert len(user_ids) > 0 or len(screen_names) > 0
        except AssertionError:
            raise ValueError('No users provided to lookup_users')

        if len(user_ids) > 0:
            for grp in ut.grouper(user_ids, 100): # max 100 per call
                twargs = dict({'method': 'lookup_users', 'user_ids': grp}, **kwargs)

                try:
                    ret = [u for u in self.make_api_call(**twargs)]
                except err.NotFoundError:
                    # Whatever the underlying Twitter endpoint's behavior is,
                    # tweepy's lookup_users normally doesn't raise errors if you
                    # pass it bad users. It just doesn't return them. It *does*
                    # raise an error if you pass it *only* bad users, but it's
                    # simpler for clients of this method to not have to handle
                    # two kinds of exception conditions. So let's return no
                    # users if all users were bad.
                    ret = []

                yield from ret

        if len(screen_names) > 0: # NOTE not elif: we want to handle both
            for grp in ut.grouper(screen_names, 100): # max 100 per call
                twargs = dict({'method': 'lookup_users', 'screen_names': grp}, **kwargs)

                try:
                    ret = [u for u in self.make_api_call(**twargs)]
                except err.NotFoundError:
                    # Same funky tweepy behavior as in the except clause above
                    ret = []

                yield from ret

    def get_list(self, full_name=None, list_id=None, slug=None,
                 owner_screen_name=None, owner_id=None, **kwargs):
        try:
            assert (full_name is not None) ^ (list_id is not None) ^ (
                    slug is not None and (
                        owner_screen_name is not None or
                        owner_id is not None
                    )
            )
        except AssertionError:
            raise ValueError('Bad list specification to get_list')

        if full_name is not None:
            owner_screen_name = full_name.split('/')[0]
            slug = full_name.split('/')[1]

        twargs = dict({
            'method': 'get_list',
            'list_id': list_id,
            'slug': slug,
            'owner_screen_name': owner_screen_name,
            'owner_id': owner_id
        }, **kwargs)

        return next(self.make_api_call(**twargs))

    def list_members(self, full_name=None, list_id=None, slug=None,
                     owner_screen_name=None, owner_id=None, **kwargs):
        try:
            assert (full_name is not None) ^ (list_id is not None) ^ (
                    slug is not None and (
                        owner_screen_name is not None or
                        owner_id is not None
                    )
            )
        except AssertionError:
            raise ValueError('Bad list specification to list_members')

        if full_name is not None:
            owner_screen_name = full_name.split('/')[0]
            slug = full_name.split('/')[1]

        twargs = dict({
            'method': 'list_members',
            'cursor': True,
            'list_id': list_id,
            'slug': slug,
            'owner_screen_name': owner_screen_name,
            'owner_id': owner_id
        }, **kwargs)

        yield from self.make_api_call(**twargs)

    def list_timeline(self, lst, **kwargs):
        msg = 'Fetching timeline of list {0}'
        logger.debug(msg.format(lst))

        twargs = dict({
            'method': 'list_members',
            'count': 200, # the max in one call
            'tweet_mode': 'extended', # don't truncate tweet text
            'include_rts': True,
            'cursor': True,
            'owner_screen_name': lst.split('/')[0],
            'slug': lst.split('/')[1]
        }, **kwargs)

        yield from self.make_api_call(**twargs)

    def user_timeline(self, user_id=None, screen_name=None, **kwargs):
        user, user_type = to_user_type(user_id, screen_name)

        msg = 'Fetching timeline of ' + user_type + ' {0}'
        logger.debug(msg.format(user))

        twargs = dict({
            'method': 'user_timeline',
            'count': 200, # per page, not total; the max in one call
            'tweet_mode': 'extended', # don't truncate tweet text
            'include_rts': True,
            'exclude_replies': False,
            'cursor': True,
            user_type: user
        }, **kwargs)

        yield from self.make_api_call(**twargs)

    def followers_ids(self, user_id=None, screen_name=None, **kwargs):
        user, user_type = to_user_type(user_id, screen_name)

        msg = 'Fetching followers of ' + user_type + ' {0}'
        logger.debug(msg.format(user))

        twargs = dict({
            'method': 'followers_ids',
            'cursor': True,
            user_type: user
        }, **kwargs)

        yield from self.make_api_call(**twargs)

    def friends_ids(self, user_id=None, screen_name=None, **kwargs):
        user, user_type = to_user_type(user_id, screen_name)

        msg = 'Fetching friends of ' + user_type + ' {0}'
        logger.debug(msg.format(user))

        twargs = dict({
            'method': 'friends_ids',
            'cursor': True,
            user_type: user
        }, **kwargs)

        yield from self.make_api_call(**twargs)

