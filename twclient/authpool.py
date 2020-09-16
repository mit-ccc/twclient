import time
import random
import logging

import tweepy

from . import error as err

logger = logging.getLogger(__name__)

# This class transparently multiplexes access to multiple sets of Twitter API
# credentials. It creates as many tweepy.API instances as it gets sets of API
# creds, and then dispatches method calls to the appropriate instance, handling
# rate limit and over-capacity errors. When one instance hits its rate limit,
# we transparently switch over to the next.

# User code can treat it as a drop-in replacement for tweepy.API.

class AuthPoolAPI(object):
    _authpool_return_types = {
        'get_list': 'single',
        'list_members': 'list',
        'lookup_users': 'list',
        'list_members': 'list',
        'user_timeline': 'list',
        'followers_ids': 'list',
        'friends_ids': 'list'
    }

    def __init__(self, **kwargs):
        try:
            auths = kwargs.pop('auths')
            assert len(auths) > 0
        except KeyError:
            raise ValueError("Must provide more than 0 Twitter credential sets")

        wait_on_rate_limit = kwargs.pop('wait_on_rate_limit', True)

        capacity_sleep = kwargs.pop('capacity_sleep', 15 * 60)
        capacity_retries = kwargs.pop('capacity_retries', 3)

        super(AuthPoolAPI, self).__init__()

        # These attributes all have an "_authpool" prefix to avoid clashing
        # with attributes of the underlying tweepy.API instances. We create
        # those instances with wait_on_rate_limit=False so that we can switch
        # between API instances on hitting the limit.

        self._authpool_wait_on_rate_limit = wait_on_rate_limit

        self._authpool_capacity_sleep = capacity_sleep
        self._authpool_capacity_retries = capacity_retries

        self._authpool_current_api_index = 0
        self._authpool_apis = [
            tweepy.API(auth, wait_on_rate_limit=False, **kwargs)

            for auth in random.sample(auths, len(auths))
        ]

        self._authpool_rate_limit_resets = [None for x in self._authpool_apis]

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
        for i in range(len(self._authpool_apis)):
            t = self._authpool_rate_limit_resets[i]

            if t is not None and t < time.time():
                self._authpool_apis[i] = None

        free_inds = [
                i
                for i, t in enumerate(self._authpool_rate_limit_resets)
                if t is None
        ]

        free_inds = random.sample(free_inds, len(free_inds))

        if len(free_inds) > 0:
            self._authpool_current_api_index = free_inds[0]
        else:
            # i.e., the one with the shortest wait for rate limit reset
            i = min(range(len(self._authpool_apis)),
                    key=lambda x: self._authpool_rate_limit_resets[x])

            # add a little fudge factor to be safe
            time.sleep(self._authpool_rate_limit_resets[i] + 0.01)

            self._authpool_current_api_index = i

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
        if not all([hasattr(x, name) for x in self._authpool_apis]):
            raise AttributeError(name)

        is_method = [
            hasattr(getattr(x, name), '__call__')
            for x in self._authpool_apis
        ]

        if not all(is_method):
            return getattr(self._authpool_current_api, name)

        # this function proxies for the tweepy methods.
        # we use "iself" to avoid confusing shadowing of the binding.
        def func(iself, *args, **kwargs):
            cp_retry_cnt = 0

            while True:
                method = getattr(iself._authpool_current_api, name)

                try:
                    ret = method(*args, **kwargs)

                    iself._authpool_mark_api_free()

                    # it's a count of *consecutive* retries since the last
                    # successful API call
                    cp_retry_cnt = 0

                    return ret
                except tweepy.error.RateLimitError as e:
                    resume_time = e.response.headers.get('x-rate-limit-reset')
                    iself._authpool_mark_api_limited(resume_time)

                    iself._authpool_switch_api()
                except tweepy.error.TweepError as e:
                    de = err.dispatch(e)

                    if not isinstance(de, err.CapacityError):
                        raise de
                    elif cp_retry_cnt >= iself._authpool_capacity_retries:
                        raise de
                    else:
                        msg = 'Over-capacity error on try {0}; sleeping {1}'
                        msg = msg.format(cp_retry_cnt, iself._authpool_capacity_sleep)
                        logger.warning(msg)

                        time.sleep(iself._authpool_capacity_sleep)

                        cp_retry_cnt += 1

        # tweepy uses attributes to control cursors and pagination, so
        # we need to set them
        methods = [getattr(x, name) for x in self._authpool_apis]
        ind = self._authpool_current_api_index

        for k, v in vars(methods[ind]).items():
            if all([k in vars(x).keys() for x in methods]):
                if all([vars(x)[k] == v for x in methods]):
                    setattr(func, k, v)

        setattr(func, 'twclient_return_type',
                self._authpool_return_types.get(name, 'unknown'))

        # the descriptor protocol: func is an unbound function, but the __get__
        # method returns func as a bound method of its argument
        setattr(self, name, func.__get__(self))

        return getattr(self, name)

