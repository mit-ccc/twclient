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

        abort_on_bad_targets = kwargs.pop('abort_on_bad_targets', False)

        super(TwitterApi, self).__init__(**kwargs)

        self.auths = auths
        self.pool = ap.AuthPoolAPI(auths=auths, wait_on_rate_limit=True)
        self.abort_on_bad_targets = abort_on_bad_targets

    def make_api_call(self, method, cursor=False, max_items=None,
                      method_returns_list=True, **kwargs):
        msg = 'API call: {0} with params {1}, cursor {2}'
        logger.debug(msg.format(method, kwargs, cursor))

        func = getattr(self.pool, method)

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

            if not method_returns_list:
                yield ret
            else:
                j = 0
                for obj in ret:
                    yield obj
                    j += 1

                # NOTE users/lookup doesn't raise an error condition on bad
                # users, it just doesn't return them, so we need to check the
                # length of the input and the number of user objects returned
                if method == 'lookup_users':
                    assert 'screen_names' in twargs.keys() or \
                        'user_ids' in twargs.keys()

                    if 'screen_names' in twargs.keys():
                        kind = 'screen_names'
                    else:
                        kind = 'user_ids'

                    # don't risk it being a generator
                    nmissing = len([x for x in twargs[kind]]) - j

                    if nmissing > 0:
                        msg = "{0} bad/missing user(s) in users/lookup call"
                        raise err.NotFoundError(msg.format(nmissing))
        except (tweepy.error.TweepError, err.TWClientError) as e:
            if isinstance(e, err.CapacityError):
                raise
            elif isinstance(e, err.ProtectedUserError):
                msg = 'Ignoring protected user in call to method {0} ' \
                      'with arguments {1}; original exception message: {2}'
                msg = msg.format(method, kwargs, e.message)
                logger.warning(msg)
            elif isinstance(e, err.NotFoundError):
                msg = 'Requested object(s) not found in call to method {0} ' \
                      'with arguments {1}; original exception message: {2}'
                msg = msg.format(method, kwargs, e.message)

                if self.abort_on_bad_targets:
                    logger.exception(msg)

                    raise
                else:
                    logger.warning(msg)
            else:
                reason = e.reason
                api_code = e.api_code
                if e.response is not None:
                    http_code = e.response.status_code
                else:
                    http_code = None

                msg = 'Error returned by Twitter API: API code {0}, HTTP ' \
                      'status code {1}, reason {2}'
                msg = msg.format(api_code, http_code, reason)

                logger.debug(msg, exc_info=True)

                raise

    ##
    ## Direct wraps of Twitter API methods
    ##

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
            'method_returns_list': False,
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
            raise ValueError('Bad list specification to get_list')

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
                yield from self.make_api_call(**twargs)

        if len(screen_names) > 0:
            for grp in ut.grouper(screen_names, 100): # max 100 per call
                twargs = dict({'method': 'lookup_users', 'screen_names': grp}, **kwargs)
                yield from self.make_api_call(**twargs)

    def list_timeline(self, lst, **kwargs):
        logger.debug('Fetching timeline of list {0}'.format(lst))

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

