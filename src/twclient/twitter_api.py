'''
A Twitter API wrapper for job classes.
'''

import logging

import tweepy

from . import error as err
from . import _utils as ut
from . import authpool as ap

logger = logging.getLogger(__name__)


@ut.export
class TwitterApi:
    '''
    Wrap calls to the Twitter API with cursoring, common parameters, etc.

    This class provides a wrapper around calls to the Twitter API (ultimately
    through tweepy) to handle cursoring of results, provide common parameters
    that all twclient requests will want, and do other housekeeping. In
    particular, it transparently multiplexes access to the passed API
    credentials (via authpool.AuthPoolAPI), with the effect of combining their
    rate limits. Not all Twitter API methods are supported.

    Parameters
    ----------
    auths : list of tweepy.AuthHandler
        The Twitter API credentials to use.

    Attributes
    ----------
    auths : list of tweepy.AuthHandler
        The parameter passed to __init__.

    pool : instance of models.AuthPoolAPI
        The AuthPoolAPI constructed with the API credentials.
    '''

    #
    # Common methods
    #

    @staticmethod
    def _to_user_type(user_id, screen_name):
        try:
            assert user_id is not None or screen_name is not None
            assert user_id is None or screen_name is None
        except AssertionError as exc:
            raise ValueError("Must provide user_id xor screen_name") from exc

        user_type = 'user_id' if user_id is not None else 'screen_name'
        user = ut.coalesce(user_id, screen_name)

        return user, user_type

    def __init__(self, **kwargs):
        try:
            auths = kwargs.pop('auths')
        except KeyError as exc:
            raise ValueError('auths argument is required') from exc

        super().__init__(**kwargs)

        self.auths = auths
        self.pool = ap.AuthPoolAPI(auths=auths)

    def make_api_call(self, method, cursor=False, max_items=None, **kwargs):
        '''
        Make a call to the Twitter API.

        This method wraps calls to the Twitter API, handling cursoring of
        results, and returns a generator of all the results returned. If there
        are a very large number of results (as in fetching follow graph data),
        using this method will avoid reading them all into memory at once. The
        calls are made through authpool.AuthPoolAPI, transparently handling use
        of multiple sets of API credentials.

        Parameters
        ----------
        method : str
            The name of the tweepy.API method to call.

        cursor : bool
            Should the results be cursored? Generally should be True if the
            method may return more than one object.

        max_items : int, or None
            If the method returns more than max_items items, should the surplus
            results be discarded? Must be None if cursor == False.

        **kwargs
            Other arguments to pass through to the tweepy method, or to
            tweepy.Cursor if cursor == True. (In the latter case, tweepy.Cursor
            will in turn pass arguments it doesn't consume through to the
            method ultimately called.)

        Yields
        ------
        instances of tweepy.Model, int, or other objects
            The results returned by the Twitter API call. The type of object
            yielded depends on the value of the method argument.
        '''

        msg = 'API call: {0} with params {1}, cursor {2}'
        msg = msg.format(method, kwargs, cursor)
        logger.debug(msg)

        func = getattr(self.pool, method)
        return_type = getattr(func, 'twclient_return_type')

        try:
            assert not (cursor and max_items is not None)
        except AssertionError as exc:
            msg = 'max_items only available with cursor=True'
            raise ValueError(msg) from exc

        try:
            if cursor and max_items is not None:
                ret = tweepy.Cursor(method=func, **kwargs).items(max_items)
            elif cursor:
                ret = tweepy.Cursor(method=func, **kwargs).items()
            else:
                ret = func(**kwargs)

            if return_type == 'single':
                yield ret
            elif return_type == 'list':
                yield from ret
            else:  # return_type == 'unknown'
                msg = f'Return type of method {method} unspecified'
                raise RuntimeError(msg)
        except Exception as exc:
            msg = f'Exception in call to Twitter API: {repr(exc)}'
            logger.debug(msg, exc_info=True)

            raise

    def rate_limit_status(self, consumer_key=None):
        '''
        Call Twitter's application/rate_limit_status method.

        This method wraps one or more calls to Twitter's API method
        application/rate_limit_status and returns information on rate limits.
        The default is to request rate limit info for all credentials given in
        the ``self.auths`` attribute. See also the method of the same name on
        ``authpool.AuthPoolAPI``, which this method calls.

        Parameters
        ----------
        consumer_key : str or None
            The consumer key for a particular set of API credentials whose rate
            limit should be checked. If None, check all credentials in
            ``self.auths``. If not None, the value must match one of the
            consumer keys in ``self.auths``.

        Returns
        -------
        dict
            A dictionary whose keys are the OAuth consumer keys and whose
            values are the Twitter API's json responses describing rate limit
            information.
        '''

        msg = 'Getting rate limits for consumer key(s): '
        msg += ('all' if consumer_key is None else consumer_key)
        logger.debug(msg)

        twargs = {
            'method' : 'rate_limit_status',
            'consumer_key' : consumer_key
        }

        return self.make_api_call(**twargs)

    #
    # Direct wraps of Twitter API methods
    #

    def lookup_users(self, user_ids=None, screen_names=None):
        '''
        Call Twitter's users/lookup API method.

        This method wraps a call to Twitter's users/lookup method (via the
        make_api_call method, and ultimately via tweepy.API's lookup_users
        method), which "hydrates" the requested users. For greater consistency,
        error handling differs from the Twitter method and from tweepy.
        Requested users which do not exist, are suspended, or are otherwise
        unavailable are not returned, without raising an error (as in both
        tweepy and the underlying Twitter API). If no requested users exist,
        no error is raised (unlike tweepy and the Twitter API), and instead an
        empty list is returned. At least one of user_ids and screen_names, or
        both, must be specified. The most recent tweet for each user is
        returned in extended mode (i.e., not truncated to 140 characters), and
        entities are requested.

        Parameters
        ----------
        user_ids : list of int, or None
            Twitter user IDs to hydrate. May be passed simultaneously with
            screen_names.

        screen_names : list of str, or None
            Twitter screen names to hydrate. May be passed simultaneously with
            user_ids.

        Yields
        ------
        list of tweepy.User
            The hydrated user objects.
        '''

        user_ids = ut.coalesce(user_ids, [])
        screen_names = ut.coalesce(screen_names, [])

        msg = 'Hydrating user_ids {0} and screen_names {1}'
        msg = msg.format(user_ids, screen_names)
        logger.debug(msg)

        try:
            assert user_ids or screen_names
        except AssertionError as exc:
            raise ValueError('No users provided to lookup_users') from exc

        if user_ids:
            for grp in ut.grouper(user_ids, 100):  # max 100 per call
                twargs = {
                    'method': 'lookup_users',
                    'include_entities': True,  # include user sub-objects
                    'tweet_mode': 'extended',  # don't truncate tweet text
                }

                if ut.TWEEPY_V4:
                    twargs['user_id'] = grp
                else:
                    twargs['user_ids'] = grp

                try:
                    ret = list(self.make_api_call(**twargs))
                except err.NotFoundError:
                    # Whatever the underlying Twitter endpoint's behavior is,
                    # tweepy's lookup_users normally doesn't raise errors if
                    # you pass it bad users. It just doesn't return them. It
                    # *does* raise an error if you pass it *only* bad users,
                    # but it's simpler for clients of this method to not have
                    # to handle two kinds of exception conditions. So let's
                    # return no users if all users were bad.
                    ret = []

                yield from ret

        if screen_names:  # NOTE not elif: we want to handle both
            for grp in ut.grouper(screen_names, 100):  # max 100 per call
                twargs = {
                    'method': 'lookup_users',
                    'include_entities': True,  # include user sub-objects
                    'tweet_mode': 'extended',  # don't truncate tweet text
                }

                if ut.TWEEPY_V4:
                    twargs['screen_name'] = grp
                else:
                    twargs['screen_names'] = grp

                try:
                    ret = list(self.make_api_call(**twargs))
                except err.NotFoundError:
                    # Same funky tweepy behavior as in the except clause above
                    ret = []

                yield from ret

    def get_list(self, list_id=None, slug=None, owner_screen_name=None,
                 owner_id=None):
        '''
        Call Twitter's lists/show API method.

        This method wraps a call to Twitter's lists/show method (via the
        make_api_call method, and ultimately via tweepy.API's get_list method).
        The target list must be specified, as in the list_members method, by
        exactly one of list_id or slug as well as exactly one of
        owner_screen_name or owner_id.

        Parameters
        ----------
        list_id : int, or None
            Twitter's integer ID for the list.

        slug : str, or None
            The slug of the list (not its display name).

        owner_screen_name : str, or None
            The screen name of the user who owns the list (without the @ sign).

        owner_id : int, or None
            Twitter's integer user ID for the user who owns the list.

        Returns
        -------
        tweepy.List object
            The hydrated list object.
        '''

        try:
            assert (list_id is not None) ^ (
                slug is not None and (
                    (owner_screen_name is not None) ^
                    (owner_id is not None)
                )
            )
        except AssertionError as exc:
            raise ValueError('Bad list specification to get_list') from exc

        twargs = {
            'method': 'get_list',
            'list_id': list_id,
            'slug': slug,
            'owner_screen_name': owner_screen_name,
            'owner_id': owner_id
        }

        return next(self.make_api_call(**twargs))

    def list_members(self, list_id=None, slug=None, owner_screen_name=None,
                     owner_id=None):
        '''
        Call Twitter's lists/members API method.

        This method wraps a call to Twitter's lists/members API method (via the
        make_api_call method and ultimately via tweepy.API's list_members
        method). The target list must be specified, as in the get_list method,
        by exactly one of list_id or slug as well as exactly one
        of owner_screen_name or owner_id.

        Parameters
        ----------
        list_id : int, or None
            Twitter's integer ID for the list.

        slug : str, or None
            The slug of the list (not its display name).

        owner_screen_name : str, or None
            The screen name of the user who owns the list (without the @ sign).

        owner_id : int, or None
            Twitter's integer user ID for the user who owns the list.

        Yields
        ------
        tweepy.User objects
            Hydrated user objects for the members of the list.
        '''

        try:
            assert (list_id is not None) ^ (
                slug is not None and (
                    (owner_screen_name is not None) ^
                    (owner_id is not None)
                )
            )
        except AssertionError as exc:
            raise ValueError('Bad list specification to list_members') from exc

        twargs = {
            'cursor': True,
            'list_id': list_id,
            'slug': slug,
            'owner_screen_name': owner_screen_name,
            'owner_id': owner_id
        }

        if ut.TWEEPY_V4:
            twargs['method'] = 'get_list_members'
        else:
            twargs['method'] = 'list_members'

        yield from self.make_api_call(**twargs)

    def user_timeline(self, user_id=None, screen_name=None, **kwargs):
        '''
        Call Twitter's statuses/user_timeline API method.

        This method wraps a call to Twitter's statuses/user_timeline API
        method (via the make_api_call method and ultimately via tweepy.API's
        user_timeline method). Exactly one of user_id and screen_name must be
        specified. Tweets are requested in extended mode (i.e., not truncated
        to 140 characters) and both retweets and replies are included. Note
        that because of a limitation in the underlying Twitter API method, if
        the user has posted and not deleted more than approximately 3200
        tweets, only the most recent approximately 3200 will be retrieved.

        Parameters
        ----------
        user_id : int, or None
            Twitter's integer user ID for the user whose tweets are to be
            retrieved.

        screen_name : str, or None
            The screen name of the user whose tweets are to be retrieved.

        **kwargs
            Further arguments to pass through to tweepy.API.user_timeline,
            possibly via tweepy.Cursor.

        Yields
        ------
        tweepy.Tweet objects
            The user's tweets.
        '''

        try:
            assert (user_id is not None) ^ (screen_name is not None)
        except AssertionError as exc:
            msg = 'Bad user specification to user_timeline'
            raise ValueError(msg) from exc

        user, user_type = self._to_user_type(user_id, screen_name)

        msg = 'Fetching timeline of ' + user_type + ' {0}'
        msg = msg.format(user)
        logger.debug(msg)

        twargs = dict({
            'method': 'user_timeline',
            'count': 200,  # per page, not total; the max in one call
            'tweet_mode': 'extended',  # don't truncate tweet text
            'include_rts': True,
            'exclude_replies': False,
            'cursor': True,
            user_type: user
        }, **kwargs)

        yield from self.make_api_call(**twargs)

    def followers_ids(self, user_id=None, screen_name=None):
        '''
        Call Twitter's followers/ids API method.

        This method wraps a call to Twitter's followers/ids API method (via the
        make_api_call method and ultimately via tweepy.API's get_follower_ids
        method / followers_ids in tweepy < 4.0.0). Exactly one of user_id and
        screen_name must be specified.

        Parameters
        ----------
        user_id : int, or None
            Twitter's integer user ID for the user whose followers' IDs are to
            be retrieved.

        screen_name : str, or None
            The screen name of the user whose followers' IDs are to be
            retrieved.

        Yields
        ------
        instances of int
            The Twitter user_ids of the requested user's followers.
        '''

        try:
            assert (user_id is not None) ^ (screen_name is not None)
        except AssertionError as exc:
            msg = 'Bad user specification to followers_ids'
            raise ValueError(msg) from exc

        user, user_type = self._to_user_type(user_id, screen_name)

        msg = 'Fetching followers of ' + user_type + ' {0}'
        msg = msg.format(user)
        logger.debug(msg)

        twargs = {
            'cursor': True,
            user_type: user
        }

        if ut.TWEEPY_V4:
            twargs['method'] = 'get_follower_ids'
        else:
            twargs['method'] = 'followers_ids'

        yield from self.make_api_call(**twargs)

    def friends_ids(self, user_id=None, screen_name=None):
        '''
        Call Twitter's friends/ids API method.

        This method wraps a call to Twitter's friends/ids API method (via the
        make_api_call method and ultimately via tweepy.API's get_friend_ids
        method / friends_ids in tweepy < 4.0.0). Exactly one of user_id and
        screen_name must be specified. Note that "friends" is Twitter's term
        for the opposite of followers: user A's friends are the users that A
        follows.

        Parameters
        ----------
        user_id : int, or None
            Twitter's integer user ID for the user whose friends' IDs are to
            be retrieved.

        screen_name : str, or None
            The screen name of the user whose friends' IDs are to be
            retrieved.

        Yields
        ------
        instances of int
            The Twitter user_ids of the requested user's friends.
        '''

        try:
            assert (user_id is not None) ^ (screen_name is not None)
        except AssertionError as exc:
            raise ValueError('Bad user specification to friends_ids') from exc

        user, user_type = self._to_user_type(user_id, screen_name)

        msg = 'Fetching friends of ' + user_type + ' {0}'
        msg = msg.format(user)
        logger.debug(msg)

        twargs = {
            'cursor': True,
            user_type: user
        }

        if ut.TWEEPY_V4:
            twargs['method'] = 'get_friend_ids'
        else:
            twargs['method'] = 'friends_ids'

        yield from self.make_api_call(**twargs)
