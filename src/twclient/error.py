'''
Exceptions that twclient code may raise
'''

import logging

import tweepy

logger = logging.getLogger(__name__)


#
# Base classes
#


class TWClientError(Exception):
    '''
    The base class for all errors raised by twclient.

    Parameters
    ----------
    message : str
        The reason for this error.

    exit_status : int
        If the exception is caught at the top-level command-line script,
        this value is passed to `sys.exit`.

    Attributes
    ----------
    message : str
        The reason for this error.

    exit_status
        If the exception is caught at the top-level command-line script,
        this value is passed to `sys.exit`.
    '''

    def __init__(self, **kwargs):
        message = kwargs.pop('message', '')
        exit_status = kwargs.pop('exit_status', 1)

        super().__init__(**kwargs)

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


#
# Twitter API errors
#


# See Twitter docs:
# https://developer.twitter.com/en/support/twitter-api/error-troubleshooting
class TwitterAPIError(TWClientError):
    '''
    Base class for errors returned by the Twitter API.

    Instances of this class correspond to errors returned by the Twitter API,
    but are higher-level and easier to handle in client code than the
    underlying instances of tweepy.error.TweepError which gave rise to them.

    Parameters
    ----------
    response : requests.Response object
        The Twitter API response which led to this error being raised.

    api_code : int
        The API code Twitter returned.

    Attributes
    ----------
    response : requests.Response object
        The Twitter API response which led to this error being raised.

    api_code : int
        The API code Twitter returned.
    '''

    _repr_attrs = ['message', 'exit_status', 'response', 'api_code',
                   'http_code']

    def __init__(self, **kwargs):
        response = kwargs.pop('response', None)
        api_code = kwargs.pop('api_code', None)

        super().__init__(**kwargs)

        self.response = response
        self.api_code = api_code

    @property
    def http_code(self):
        '''
        The HTTP status code Twitter returned with this error.
        '''

        if self.response is not None:
            return self.response.status_code

        return None

    @classmethod
    def from_tweepy(cls, exc):
        '''
        Construct an instance from a tweepy exception object.

        Parameters
        ----------
        exc : instance of tweepy.error.TweepError
            The exception from which to generate a TwitterAPIError instance.

        Returns
        -------
        Instance of the appropriate subclass of TwitterAPIError.
        '''

        return cls(message=exc.reason, response=exc.response,
                   api_code=exc.api_code)

    # This method is intended to be implemented by subclasses as their core
    # piece of logic, so the implementation here raises NotImplementedError.
    # Note that while the subclass methods are mostly right, they may not cover
    # all edge cases, because Twitter's API documentation is frequently
    # incomplete.
    @staticmethod
    def tweepy_is_instance(exc):
        '''
        Check whether a tweepy exception object can be converted to this class
        via from_tweepy().

        Parameters
        ----------
        exc : instance of tweepy.error.TweepError
            The tweepy exception object to check.

        Returns
        -------
        True if exc is convertible, False otherwise : Boolean.
        '''

        raise NotImplementedError()


class TwitterServiceError(TwitterAPIError):  # pylint: disable=abstract-method
    '''
    A problem with the Twitter service.

    A request to the Twitter service encountered a problem which was with the
    service rather than the request itself. Generally requests encountering
    this error should be retried.
    '''

    pass


class ReadFailureError(TwitterServiceError):
    '''
    A low-level network problem occurred in communicating with the Twitter API.

    Something went wrong at a low level during communication with the Twitter
    API and no sensible response could be retrieved.
    '''

    @staticmethod
    def tweepy_is_instance(exc):
        return exc.response is None


class CapacityError(TwitterServiceError):
    '''
    The Twitter API is temporarily over capacity.

    This error is raised when Twitter's API indicates that it's over capacity
    and cannot fulfill a request. Code catching this exception should generally
    sleep a reasonable period of time and retry the request.
    '''

    @staticmethod
    def tweepy_is_instance(exc):
        return \
            exc.api_code in (130, 131) or \
            (
                exc.response is not None and
                exc.response.status_code in (500, 503, 504)
            )


class TwitterLogicError(TwitterAPIError):  # pylint: disable=abstract-method
    '''
    A request to the Twitter service encountered a logical error condition.

    This error is raised when a request to the Twitter service was received and
    executed successfully but returned a logical error condition. For example,
    requesting tweets from a user with protected tweets will raise a subclass
    of this exception class.
    '''

    pass


class NotFoundError(TwitterLogicError):
    '''
    A requested object was not found.

    There are several ways Twitter indicates that a requested object was not
    found, involving some combination of the API response code, the HTTP status
    code, and the message. Code in twclient generally can tell from context
    what object was not found, so we combine these errors into one class.
    '''

    @staticmethod
    def tweepy_is_instance(exc):
        return \
            exc.api_code in (17, 34, 50, 63) or \
            (
                exc.api_code is None and
                exc.response is not None and
                exc.response.status_code == 404
            )


# That is, accessing protected users' friends, followers, or tweets returns
# an HTTP 401 with message "Not authorized." and no Twitter status code.
class ProtectedUserError(TwitterLogicError):
    '''
    A requested user has protected tweets.

    Requesting information about a user with protected tweets is not always an
    error; certain kinds of information will be returned. But tweets and
    friends/followers will not be and instead will raise this error.
    '''

    @staticmethod
    def tweepy_is_instance(exc):
        return \
            exc.api_code is None and \
            exc.response is not None and \
            exc.response.status_code == 401


def dispatch_tweepy(exc):
    '''
    Take an exception class and convert it to a TWClientError if applicable.

    This class takes in an arbitrary exception ex and dispatches it in the
    following way: a) if ex is a tweepy.error.TweepError, convert it to the
    corresponding TWClientError if possible, else b) return ex as-is. It is
    used in wrappers of the Twitter API to simplify exception handling.

    Parameters
    ----------
    ex : Exception
        The exception instance to dispatch.

    Returns
    -------
    Exception
        The dispatched (possibly new) exception instance.
    '''

    if not isinstance(exc, tweepy.error.TweepError):
        return exc

    klasses = [ReadFailureError, NotFoundError, ProtectedUserError,
               CapacityError]

    for kls in klasses:
        if kls.tweepy_is_instance(exc):
            return kls.from_tweepy(exc)

    return exc


#
# Higher-level errors
#


class SemanticError(TWClientError):
    '''
    Base class for non-Twitter error conditions.

    These errors indicate larger problems with the operation of the program
    than a specific Twitter or database error (though such an error may have
    led to this one being raised).
    '''

    pass


class BadTargetError(SemanticError):
    '''
    A specified target user is protected, suspended or otherwise nonexistent.

    This error is raised when a user targeted for `fetch` is found to be
    unavailable. There may be several reasons for unavailability: a user having
    protected tweets, being suspended, or otherwise not existing.

    Parameters
    ----------
    targets : list of str or int
        The Twitter user IDs or screen names causing the error.
    '''

    def __init__(self, **kwargs):
        targets = kwargs.pop('targets', [])

        super().__init__(**kwargs)

        self.targets = targets


class BadTagError(SemanticError):
    '''
    A requested tag does not exist.

    This error is raised when job.ApplyTagJob is given a tag which does not
    exist in the database.

    Parameters
    ----------
    tag : str
        The name of the nonexistent tag.

    Attributes
    ----------
    tag : str
        The name of the nonexistent tag.
    '''

    def __init__(self, **kwargs):
        tag = kwargs.pop('tag', None)

        super().__init__(**kwargs)

        self.tag = tag


class BadSchemaError(SemanticError):
    '''
    The database schema is corrupt or the wrong version.

    This error is raised when a Job detects that the schema present in the
    selected database profile is corrupt, an unsupported version, or not a
    twclient schema.
    '''

    pass
