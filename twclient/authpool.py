import time
import logging

import tweepy

import twclient.error as err

fmt = '%(asctime)s : %(module)s : %(levelname)s : %(message)s'
logging.basicConfig(format=fmt, level=logging.WARNING)
logger = logging.getLogger(__name__)

# This class transparently multiplexes access to multiple sets of Twitter API
# credentials. It creates as many tweepy.API instances as it gets sets of API
# creds, and then dispatches method calls to the appropriate instance, handling
# rate limit and over-capacity errors. When one instance hits its rate limit,
# we transparently switch over to the next.

# User code can treat it as a drop-in replacement for tweepy.API.

class AuthPoolAPI(object):
    def __init__(self, **kwargs):
        try:
            auths = kwargs.pop('auths')
            assert len(auths) > 0
        except KeyError:
            raise ValueError("Must provide auths")

        rate_limit_sleep = kwargs.pop('rate_limit_sleep', 15 * 60)
        rate_limit_retries = kwargs.pop('rate_limit_retries', 3)

        capacity_sleep = kwargs.pop('capacity_sleep', 15 * 60)
        capacity_retries = kwargs.pop('capacity_retries', 3)

        super(AuthPoolAPI, self).__init__()

        # These attributes all have an "_authpool" prefix to avoid clashing
        # with attributes of the underlying tweepy.API instances

        self._authpool_rate_limit_sleep = rate_limit_sleep
        self._authpool_rate_limit_retries = rate_limit_retries

        self._authpool_capacity_sleep = capacity_sleep
        self._authpool_capacity_retries = capacity_retries

        self._authpool_apis = [tweepy.API(auth, **kwargs) for auth in auths]
        self._authpool_current_api_index = 0

    @property
    def _authpool_current_api(self):
        return self._authpool_apis[self._authpool_current_api_index]

    # i.e., + 1 mod(# of apis)
    def _authpool_next_api(self):
        self._authpool_current_api_index += 1

        if self._authpool_current_api_index >= len(self._authpool_apis):
            self._authpool_current_api_index -= len(self._authpool_apis)

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
            # rate limit retry counts are API instance specific, but if
            # Twitter returns a capacity error, that applies to the whole
            # service however we access it
            #rl_retry_cnt = [0 for x in self._authpool_apis]
            rl_retry_cnt = 0
            cp_retry_cnt = 0

            while True:
                method = getattr(iself._authpool_current_api, name)

                try:
                    ret = method(*args, **kwargs)

                    # it's a count of *consecutive* retries since the last
                    # successful API call
                    cp_retry_cnt = 0

                    return ret
                except tweepy.error.RateLimitError:
                    # retry with the next API object in line
                    iself._authpool_next_api()
                except tweepy.error.TweepError as e:
                    if err.is_probable_capacity_error(e):
                        if cp_retry_cnt < iself._authpool_capacity_retries:
                            msg = 'Capacity error on try {0}; sleeping {1}'
                            msg = msg.format(cp_retry_cnt, iself._authpool_capacity_sleep)
                            logger.warning(msg)

                            time.sleep(iself._authpool_capacity_sleep)

                            cp_retry_cnt += 1
                        else:
                            msg = 'Capacity error in call to {0}'.format(name)
                            raise err.CapacityError(msg)
                    else:
                        raise

                # FIXME this isn't quite right: what if rate limited several
                # times widely separated in time, with successful calls in
                # between?

                # we've tried all API objects and been rate
                # limited on all of them, back to the 0th one
                if iself._authpool_current_api_index == 0:
                    if rl_retry_cnt < iself._authpool_rate_limit_retries:
                        msg = 'Rate limited on try {0}; sleeping {1}'
                        msg = msg.format(rl_retry_cnt, iself._authpool_rate_limit_sleep)
                        logger.warning(msg)

                        time.sleep(iself._authpool_rate_limit_sleep)

                        rl_retry_cnt += 1
                    else:
                        msg = 'Rate limited in call to {0}'.format(name)
                        raise err.RateLimitError(msg)

        # tweepy uses attributes to control cursors and pagination, so
        # we need to set them
        methods = [getattr(x, name) for x in self._authpool_apis]

        attribs = {}
        for k, v in vars(methods[0]).items():
            if all([k in vars(x).keys() for x in methods]):
                if all([vars(x)[k] == v for x in methods]):
                    setattr(func, k, v)

        # This is where the magic happens: the call to func.__get__ returns
        # a version of func as a bound method of self
        setattr(self, name, func.__get__(self))

        return getattr(self, name)

