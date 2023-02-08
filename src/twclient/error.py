'''
Exceptions that twclient code may raise.
'''

import logging

from . import _utils as ut

if ut.TWEEPY_V4:
    # tweepy.error (< 4.0.0) became tweepy.errors in 4.0.0, so the installed
    # package will have one or the other but not both. We want pylint to avoid
    # freaking out when it can't find the missing one.

    # pylint: disable-next=import-error,no-name-in-module
    from tweepy.errors import (TweepyException, TwitterServerError, Forbidden,
                               Unauthorized, NotFound)
else:
    # pylint: disable-next=import-error,no-name-in-module
    from tweepy.error import TweepError

logger = logging.getLogger(__name__)


#
# Base classes
#

@ut.export
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
@ut.export
class TwitterAPIError(TWClientError):
    '''
    Base class for errors returned by the Twitter API.

    Instances of this class correspond to errors returned by the Twitter API,
    but are higher-level and easier to handle in client code than the
    underlying instances of tweepy.errors.TweepyException (in tweepy < 4.0.0,
    it's instead tweepy.error.TweepError) which gave rise to them.

    Parameters
    ----------
    tweepy_exception : instance of tweepy.errors.TweepyException
    (tweepy.error.TweepError in tweepy < 4.0.0)
        The underlying tweepy exception instance which caused this error to be
        raised.

    Attributes
    ----------
    tweepy_exception : instance of tweepy.errors.TweepyException
    (tweepy.error.TweepError in tweepy < 4.0.0)
        The parameter passed to __init__.
    '''

    _repr_attrs = ['message', 'exit_status', 'tweepy_exception']

    def __init__(self, **kwargs):
        tweepy_exception = kwargs.pop('tweepy_exception', None)

        if ut.TWEEPY_V4:
            message = '\n'.join(tweepy_exception.api_messages)
        else:
            message = tweepy_exception.reason

        super().__init__(message=message, **kwargs)

        self.tweepy_exception = tweepy_exception

    @property
    def response(self):
        '''
        The requests.Response object resulting from calling the Twitter API.
        '''

        return self.tweepy_exception.response

    @property
    def http_code(self):
        '''
        The HTTP status code Twitter returned with this error.
        '''

        if self.response is not None:
            ret = self.response.status_code
        else:
            ret = None

        return ret

    @property
    def api_codes(self):
        '''
        Error codes returned by the Twitter API.
        '''

        if ut.TWEEPY_V4:
            ret = self.tweepy_exception.api_codes
        else:
            ret = [self.tweepy_exception.api_code]

        return ret

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

        return cls(tweepy_exception=exc)

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


@ut.export
class TwitterServiceError(TwitterAPIError):
    '''
    A problem with the Twitter service.

    A request to the Twitter service encountered a problem which was with the
    service rather than the request itself. Examples include low-level network
    problems, over-capacity errors, and internal Twitter server problems.
    Generally requests encountering this error should be retried.
    '''

    @staticmethod
    def tweepy_is_instance(exc):
        if ut.TWEEPY_V4:
            api_codes = exc.api_codes
        else:
            api_codes = [exc.api_code]

        if ut.TWEEPY_V4 and isinstance(exc, TwitterServerError):
            ret = True
        elif exc.response is None:  # something went very wrong somewhere
            ret = True
        elif exc.response.status_code >= 500:
            # This is the HTTP status code. From Twitter docs: 500 = general
            # internal server error, 502 = down esp for maintenance, 503 = over
            # capacity, 504 = bad gateway
            ret = True
        elif 130 in api_codes:
            ret = True  # over capacity
        elif 131 in api_codes:
            ret = True  # other internal error
        else:
            ret = False

        return ret


@ut.export
class TwitterLogicError(TwitterAPIError):  # pylint: disable=abstract-method
    '''
    A request to the Twitter service encountered a logical error condition.

    This error is raised when a request to the Twitter service was received and
    executed successfully but returned a logical error condition. For example,
    requesting tweets from a user with protected tweets will raise a subclass
    of this exception class.
    '''

    pass


@ut.export
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
        if ut.TWEEPY_V4:
            ret = isinstance(exc, NotFound)
        else:
            if exc.response is not None and exc.response.status_code == 404:
                ret = True  # the HTTP status code
            elif exc.api_code == 17:  # NOTE api_codes in >= 4.0.0
                ret = True  # "No user matches for specified terms."
            elif exc.api_code == 34:
                ret = True  # "Sorry, that page does not exist."
            elif exc.api_code == 50:
                ret = True  # "User not found."
            elif exc.api_code == 63:
                ret = True  # "User has been suspended."
            else:
                ret = False

        return ret


# That is, accessing protected users' friends, followers, or tweets returns
# an HTTP 401 with message "Not authorized." and no Twitter status code.
@ut.export
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
        if ut.TWEEPY_V4:
            ret = (isinstance(exc, (Forbidden, Unauthorized)))
        else:
            ret = exc.response.status_code in (401, 403)

        return ret


@ut.export
def dispatch_tweepy_exception(exc):
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

    if ut.TWEEPY_V4:
        tweepy_exc_klass = TweepyException
    else:
        tweepy_exc_klass = TweepError

    if not isinstance(exc, tweepy_exc_klass):
        return exc

    # the list of leaf classes to consider instantiating
    klasses = [TwitterServiceError, NotFoundError, ForbiddenError]

    for kls in klasses:
        if kls.tweepy_is_instance(exc):
            return kls.from_tweepy(exc)

    return exc


#
# Higher-level errors
#


@ut.export
class SemanticError(TWClientError):
    '''
    Base class for non-Twitter error conditions.

    These errors indicate larger problems with the operation of the program
    than a specific Twitter or database error (though such an error may have
    led to this one being raised).
    '''

    pass


@ut.export
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


@ut.export
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


@ut.export
class BadSchemaError(SemanticError):
    '''
    The database schema is corrupt or the wrong version.

    This error is raised when a Job detects that the schema present in the
    selected database profile is corrupt, an unsupported version, or not a
    twclient schema.
    '''

    pass


@ut.export
class BadConfigError(SemanticError):
    '''
    An operation on the config file encountered an error.

    This error is raised when an operation to be performed on the config file
    is misspecified, impossible, encounters another error, or the config file
    is malformed.
    '''

    pass
