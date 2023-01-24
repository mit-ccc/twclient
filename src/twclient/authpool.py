'''
A version of tweepy.API with support for multiple sets of credentials.
'''

import time
import random
import logging

import tweepy

from . import _utils as ut
from . import error as err

logger = logging.getLogger(__name__)

# The dynamic method construction in AuthPoolAPI confuses the linter
# pylint: disable=protected-access

# Either tweepy.error or tweepy.errors will be missing depending on the
# version and we want pylint not to freak out when it can't find exactly
# one of them.
if ut.TWEEPY_V4:
    # pylint: disable-next=no-member
    RateLimitError = tweepy.errors.TooManyRequests

    # pylint: disable-next=no-member
    TweepyException = tweepy.errors.TweepyException
else:
    # pylint: disable-next=no-member
    RateLimitError = tweepy.error.RateLimitError

    # pylint: disable-next=no-member
    TweepyException = tweepy.error.TweepError


@ut.export
class AuthPoolAPI:
    '''
    A version of ``tweepy.API`` with support for multiple sets of credentials.

    This class transparently proxies access to multiple sets of Twitter API
    credentials. It creates as many ``tweepy.API`` instances as it gets sets of
    API credentials, and then dispatches method calls to the appropriate
    instance, handling rate limit and over-capacity errors. When one instance
    hits its rate limit, this implementation transparently switches over to the
    next. User code can treat it as a drop-in replacement for ``tweepy.API``;
    see the tweepy documentation for methods.

    Note that it does, however, handle the ``rate_limit_status`` method
    differently. We do this because it's not useful to see rate limit info for
    only one set of credentials when the point of this class is to pool
    multiple sets. Rather than return only the Twitter API response for the
    currently active set of credentials, ``rate_limit_status`` returns a
    dictionary whose keys are the consumer keys of the credentials and whose
    values are the ``rate_limit_status`` responses for those keys.

    Parameters
    ----------
    auths : list of tweepy.AuthHandler
        The Twitter API credentials to use.

    capacity_sleep : float
        How long to sleep before retrying after a Twitter capacity error, in
        seconds.

    capacity_retries : int
        How many times to retry on capacity error before giving up.

    **kwargs
        Keyword arguments passed through to tweepy.API.

    Raises
    ------
    error.TwitterServiceError
        If Twitter is over capacity or encounters other internal problems for
        longer than (approximately) `capacity_retries * capacity_sleep`
        seconds.
    '''

    # This value is set as an attribute on methods constructed and returned by
    # __getattr__ to provide advice to code in twitter_api.py.
    _authpool_return_types = {
        'get_list': 'single',
        'lookup_users': 'list',
        'user_timeline': 'list',

        'rate_limit_status': 'single',

        # the tweepy < 4.0.0 names
        'followers_ids': 'list',
        'friends_ids': 'list',
        'list_members': 'list',

        # the tweepy >= 4.0.0 names
        'get_follower_ids': 'list',
        'get_friend_ids': 'list',
        'get_list_members': 'list',
    }

    def __init__(self, **kwargs):
        try:
            auths = kwargs.pop('auths')
            assert auths
        except (KeyError, AssertionError) as exc:
            msg = "Must provide one or more Twitter credential sets"
            raise ValueError(msg) from exc

        capacity_sleep = kwargs.pop('capacity_sleep', 15 * 60)
        capacity_retries = kwargs.pop('capacity_retries', 3)

        super().__init__()

        # These attributes all have an "_authpool" prefix to avoid clashing
        # with attributes of the underlying tweepy.API instances. We create
        # those instances with wait_on_rate_limit=False so that we can switch
        # between API instances on hitting the limit.

        self._authpool_capacity_sleep = capacity_sleep
        self._authpool_capacity_retries = capacity_retries

        self._authpool_current_api_index = 0
        self._authpool_apis = [
            tweepy.API(auth, wait_on_rate_limit=False, **kwargs)

            for auth in random.sample(auths, len(auths))
        ]

        self._authpool_rate_limit_resets = [
            None
            for x in self._authpool_apis
        ]

    @property
    def _authpool_auths(self):
        return [api.auth for api in self._authpool_apis]

    @property
    def _authpool_current_api(self):
        return self._authpool_apis[self._authpool_current_api_index]

    def _authpool_mark_api_free(self):
        ind = self._authpool_current_api_index
        self._authpool_rate_limit_resets[ind] = None

    def _authpool_mark_api_limited(self, resume_time):
        ind = self._authpool_current_api_index
        self._authpool_rate_limit_resets[ind] = resume_time

    def _authpool_switch_api(self):
        for ind in enumerate(self._authpool_apis):
            reset_time = self._authpool_rate_limit_resets[ind]

            if reset_time is not None and reset_time < time.time():
                self._authpool_apis[ind] = None

        free_inds = [
            i
            for i, t in enumerate(self._authpool_rate_limit_resets)
            if t is None
        ]

        if free_inds:
            new_ind = random.sample(free_inds, 1)[0]
        else:
            # i.e., the one with the shortest wait for rate limit reset
            new_ind = min(range(len(self._authpool_apis)),
                          key=lambda x: self._authpool_rate_limit_resets[x])

            # add a little fudge factor to be safe
            wake_time = self._authpool_rate_limit_resets[new_ind] + 0.01
            msg = f'Sleeping {wake_time} seconds for rate limit'
            logger.info(msg)

            time.sleep(wake_time)

        self._authpool_current_api_index = new_ind

    # We want to transparently proxy method calls to the underlying instances
    # of tweepy.API. To do that, first check if the requested attribute is a
    # method; if not, return it. If it is, we need to wrap it in some logic
    # to handle a) credential-switching on being rate limited and b) sleeping
    # on hitting an over-capacity error. To make this work seamlessly, we need
    # a different method for each underlying method of tweepy.API.
    #
    # Rather than write those out by hand and maintain all of them, this
    # implementation dynamically constructs the appropriate method and sets it
    # on self via the descriptor protocol. The methods don't exist until called
    # and then are created and set JIT.
    def __getattr__(self, name):
        if not all(hasattr(x, name) for x in self._authpool_apis):
            raise AttributeError(name)

        is_method = [
            hasattr(getattr(x, name), '__call__')
            for x in self._authpool_apis
        ]

        if not all(is_method):
            return getattr(self._authpool_current_api, name)

        # this function proxies for whatever tweepy method was requested.
        # we use "iself" to avoid confusing shadowing of the binding of "self"
        # to __getattr__'s first argument. docstring is set dynamically below.
        def func(iself, *args, **kwargs):  # pylint: disable=missing-docstring
            # NOTE we want to provide the rate limits for all APIs at once; it
            # doesn't make a lot of sense to ask for only one credential set's
            # rate limit when the whole point of this class is to pool them
            if name == 'rate_limit_status':
                consumer_key = kwargs.pop('consumer_key', None)

                ret = {
                    api.auth.consumer_key : api.rate_limit_status()
                    for api in iself._authpool_apis
                }

                if consumer_key is not None:
                    ret = { consumer_key : ret[consumer_key] }

                return ret

            cp_retry_cnt = 0
            while True:
                try:
                    method = getattr(iself._authpool_current_api, name)
                    ret = method(*args, **kwargs)

                    iself._authpool_mark_api_free()

                    # it's a count of *consecutive* retries since the last
                    # successful API call
                    cp_retry_cnt = 0

                    return ret
                except RateLimitError as exc:
                    resume_time = exc.response.headers \
                                     .get('x-rate-limit-reset')
                    iself._authpool_mark_api_limited(float(resume_time))

                    iself._authpool_switch_api()
                except TweepyException as exc:
                    dexc = err.dispatch_tweepy_exception(exc)

                    if not isinstance(dexc, err.TwitterServiceError):
                        raise dexc from exc

                    if cp_retry_cnt >= iself._authpool_capacity_retries:
                        raise dexc from exc

                    msg = 'Over-capacity or Twitter service error on try ' \
                          '{0}; sleeping {1}'
                    msg = msg.format(cp_retry_cnt,
                                     iself._authpool_capacity_sleep)
                    logger.warning(msg)

                    time.sleep(iself._authpool_capacity_sleep)

                    cp_retry_cnt += 1

        # set the docstring
        docstring = '''
        This method proxies for an underlying method of tweepy.API.

        The tweepy.API method's docstring follows:
        '''

        # the docstring is the same on all API instances, doesn't matter which
        # one we use
        tweepy_docstring = getattr(self._authpool_current_api, name).__doc__
        tweepy_docstring = ut.coalesce(tweepy_docstring, '')

        func.__doc__ = docstring + tweepy_docstring

        # tweepy uses attributes to control cursors and pagination, so
        # we need to set them
        methods = [getattr(x, name) for x in self._authpool_apis]
        ind = self._authpool_current_api_index

        for key, value in vars(methods[ind]).items():
            if all(key in vars(x).keys() for x in methods):
                if all(vars(x)[key] == value for x in methods):
                    setattr(func, key, value)

        # we use this attribute as a hint to TwitterApi.make_api_call
        setattr(func, 'twclient_return_type',
                self._authpool_return_types.get(name, 'unknown'))

        # the descriptor protocol: func is an unbound function, but the __get__
        # method returns func as a bound method of its argument
        setattr(self, name, func.__get__(self, AuthPoolAPI))

        return getattr(self, name)
