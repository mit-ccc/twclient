import logging

logger = logging.getLogger(__name__)

##
## Various types of errors we encounter
##

# The tweepy_is_instance methods are mostly right but may not cover all edge
# cases, because Twitter's API documentation is frustratingly incomplete.

# Note in particular that attempts to access protected users' friends,
# followers, or tweets come back as an HTTP 401 with message "Not authorized."
# and no Twitter status code.

# See Twitter docs: https://developer.twitter.com/en/support/twitter-api/error-troubleshooting

##
## Base class for exceptions
##

class TWClientError(Exception):
    def __init__(self, **kwargs):
        message = kwargs.pop('message', '')
        exit_status = kwargs.pop('exit_status', 1)

        super(TWClientError, self).__init__(**kwargs)

        self.message = message
        self.exit_status = exit_status

    _repr_attrs = ['message', 'exit_status']

    def __repr__(self):
        cls = type(self).__name__

        arg_string = ', '.join([
            a + ' = ' + repr(getattr(self, a))
            for a in self._repr_attrs
        ])

        return cls + '(' + arg_string + ')'

##
## Exceptions and functions related to the Twitter API
##

class TwitterAPIError(TWClientError):
    _repr_attrs = ['message', 'exit_status', 'response', 'api_code',
                   'http_code']

    def __init__(self, **kwargs):
        response = kwargs.pop('response', None)
        api_code = kwargs.pop('api_code', None)

        super(TwitterAPIError, self).__init__(**kwargs)

        self.response = response
        self.api_code = api_code

    @property
    def http_code(self):
        if e.response is not None:
            return e.response.status_code
        else:
            return None

    @classmethod
    def from_tweepy(cls, ex):
        return cls(message=ex.reason, response=ex.response, api_code=ex.api_code)

    @staticmethod
    def tweepy_is_instance(ex):
        raise NotImplementedError()

class NotFoundError(TwitterAPIError):
    @staticmethod
    def tweepy_is_instance(ex):
        return ex.api_code in (17, 34, 50, 63) or \
            (ex.api_code is None and ex.response.status_code == 404)

class ProtectedUserError(TwitterAPIError):
    @staticmethod
    def tweepy_is_instance(ex):
        return ex.api_code is None and ex.response.status_code == 401

class CapacityError(TwitterAPIError):
    @staticmethod
    def tweepy_is_instance(ex):
        return ex.api_code in (130, 131) or \
            ex.response.status_code in (500, 503, 504)

def dispatch(ex):
    if isinstance(ex, TWClientError):
        return ex
    elif NotFoundError.tweepy_is_instance(ex):
        return NotFoundError.from_tweepy(ex)
    elif ProtectedUserError.tweepy_is_instance(ex):
        return ProtectedUserError.from_tweepy(ex)
    elif CapacityError.tweepy_is_instance(ex):
        return CapacityError.from_tweepy(ex)
    else:
        return ex

##
## Other error conditions
##

class BadTargetError(TWClientError):
    pass

