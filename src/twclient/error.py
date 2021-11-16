'''
Exceptions that twclient code may raise.
'''

import logging

import tweepy

logger = logging.getLogger(__name__)


#
# Base classes
#

if tweepy.__version__ >= '4.0.0':
    TweepyException = tweepy.errors.TweepyException
else:
    TweepyException = tweepy.error.TweepError


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
        The parameter passed to __init__.

    exit_status
        The parameter passed to __init__.
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
    underlying instances of tweepy.errors.TweepyException (in tweepy < 4.0.0,
    it's instead tweepy.error.TweepError) which gave rise to them.

    Parameters
    ----------
    response : requests.Response object
        The Twitter API response which led to this error being raised.

    api_errors : list of dict with keys str and values int or str
        The json error objects Twitter returned. May be None in tweepy versions
        < 4.0.0.

    api_codes : list of int
        The API code Twitter returned.

    api_messages : list of str
        The error messages Twitter returned.

    Attributes
    ----------
    response : requests.Response object
        The parameter passed to __init__.

    api_errors : list of dict with keys str and values int or str
        The parameter passed to __init__.

    api_codes : list of int
        The parameter passed to __init__.

    api_messages : list of int
        The parameter passed to __init__.

    message : str
        The message or concatenated set of messages Twitter returned with this
        error.
    '''

    _repr_attrs = ['message', 'exit_status', 'response', 'api_codes',
                   'http_code']

    def __init__(self, **kwargs):
        response = kwargs.pop('response', None)
        api_errors = kwargs.pop('api_errors', None)
        api_codes = kwargs.pop('api_codes', None)
        api_messages = kwargs.pop('api_messages', None)

        super().__init__(message='\n'.join(api_messages), **kwargs)

        self.response = response
        self.api_errors = api_errors
        self.api_codes = api_codes
        self.api_messages = api_messages

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
        exc : instance of tweepy.errors.TweepyException (in tweepy < 4.0.0,
        tweepy.error.TweepError)
            The exception from which to generate a TwitterAPIError instance.

        Returns
        -------
        Instance of the appropriate subclass of TwitterAPIError.
        '''

        if tweepy.__version__ >= '4.0.0':
            return cls(
                response=exc.response,
                api_errors=exc.api_errors,
                api_codes=exc.api_codes,
                api_messages=exc.api_messages
            )
        else:
            return cls(
                response=exc.response,
                api_errors=None,
                api_codes=[exc.api_code],
                api_messages=[exc.reason]
            )

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
        exc : instance of tweepy.errors.TweepyException (in tweepy < 4.0.0,
        tweepy.error.TweepError)
            The tweepy exception object to check.

        Returns
        -------
        Boolean
            True if exc is convertible, False otherwise.
        '''

        raise NotImplementedError()


class TwitterServiceError(TwitterAPIError):  # pylint: disable=abstract-method
    '''
    A problem with the Twitter service.

    A request to the Twitter service encountered a problem which was with the
    service rather than the request itself. Examples include low-level network
    problems, over-capacity errors, and internal Twitter server problems.
    Generally requests encountering this error should be retried.
    '''

    @staticmethod
    def tweepy_is_instance(exc):
        if tweepy.__version__ >= '4.0.0':
            if isinstance(exc, tweepy.errors.TwitterServerError):
                return True

        # Keep looking, either in tweepy < 4.0.0 or if something weird happens
        # in new tweepy

        if exc.response is None:  # something went very wrong somewhere
            return True

        # This is the HTTP status code. From Twitter docs: 500 = general
        # internal server error, 502 = down esp for maintenance, 503 = over
        # capacity, 504 = bad gateway
        if exc.response.status_code >= 500:
            return True

        if 130 in exc.api_codes:  # over capacity
            return True

        if 131 in exc.api_codes:  # other internal error
            return True

        return False


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
        if tweepy.__version__ >= '4.0.0':
            if isinstance(exc, tweepy.errors.NotFound):
                return True

        # the HTTP status code
        if exc.response is not None and exc.response.status_code == 404:
            return True

        if 17 in exc.api_codes:  # "No user matches for specified terms."
            return True

        if 34 in exc.api_codes:  # "Sorry, that page does not exist."
            return True

        if 50 in exc.api_codes:  # "User not found."
            return True

        if 63 in exc.api_codes:  # "User has been suspended."
            return True

        return False


# That is, accessing protected users' friends, followers, or tweets returns
# an HTTP 401 with message "Not authorized." and no Twitter status code.
class ForbiddenError(TwitterLogicError):
    '''
    A request was forbidden.

    This frequently occurs when trying to request tweets or friends/followers
    for users with private accounts / protected tweets. Requesting information
    about a user with protected tweets is not always an error; certain kinds of
    information will be returned. But tweets and friends/followers will not be
    and instead will raise this error.
    '''

    @staticmethod
    def tweepy_is_instance(exc):
        if tweepy.__version__ >= '4.0.0':
            if isinstance(exc, tweepy.errors.Forbidden):
                return True

            if isinstance(exc, tweepy.errors.Unauthorized):
                return True

        if exc.response.status_code in (401, 403):
            return True

        return False


def dispatch_tweepy(exc):
    '''
    Take an exception instance and convert it to a TWClientError if applicable.

    This class takes in an arbitrary exception ex and dispatches it in the
    following way: a) if ex is a tweepy.errors.TweepyException (in tweepy <
    4.0.0, it's instead tweepy.error.TweepError), convert it to the
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

    if not isinstance(exc, TweepyException):
        return exc

    klasses = [TwitterServiceError, NotFoundError, ForbiddenError]

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

    Attributes
    ----------
    targets : list of str or int
        The parameter passed to __init__.
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
        The parameter passed to __init__.
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
