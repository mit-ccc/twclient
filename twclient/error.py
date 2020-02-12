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

# See Twitter docs: https://developer.twitter.com/en/docs/basics/response-codes

class TWClientError(Exception):
    def __init__(self, message, response=None, api_code=None):
        self.message = message
        self.response = response
        self.api_code = api_code

        super(TWClientError, self).__init__(message)

    @classmethod
    def from_tweepy(cls, ex):
        return cls(ex.reason, ex.response, ex.api_code)

    @staticmethod
    def tweepy_is_instance(ex):
        raise NotImplementedError()

class BadUserError(TWClientError):
    @staticmethod
    def tweepy_is_instance(ex):
        return ex.api_code in (17, 34, 50, 63) or \
            (ex.api_code is None and ex.response.status_code == 404)

class ProtectedUserError(TWClientError):
    @staticmethod
    def tweepy_is_instance(ex):
        return ex.api_code is None and ex.response.status_code == 401

class CapacityError(TWClientError):
    @staticmethod
    def tweepy_is_instance(ex):
        return ex.api_code in (130, 131) or \
            ex.response.status_code in (500, 503, 504)

def dispatch(ex):
    if isinstance(ex, TWClientError):
        return ex
    elif BadUserError.tweepy_is_instance(ex):
        return BadUserError.from_tweepy(ex)
    elif ProtectedUserError.tweepy_is_instance(ex):
        return ProtectedUserError.from_tweepy(ex)
    elif CapacityError.tweepy_is_instance(ex):
        return CapacityError.from_tweepy(ex)
    else:
        return ex

