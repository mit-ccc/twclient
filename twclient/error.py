##
## Base class for any further custom exceptions
##

class TWClientError(Exception):
    pass

##
## Definitions of error classes
##

# These functions take in a tweepy.error.TweepError instance and return True or
# False to indicate whether it's the sort of error we're interested in. They're
# mostly right but may not cover all edge cases, because Twitter's API
# documentation is frustratingly incomplete.

# Note in particular that attempts to access protected users' friends,
# followers, or tweets come back as an HTTP 401 with message "Not authorized."
# and no Twitter status code.

# See Twitter docs: https://developer.twitter.com/en/docs/basics/response-codes

def is_bad_user_error(ex):
    return ex.api_code in (17, 34)

def is_protected_user_error(ex):
    return ex.api_code is None and ex.response.status_code == 401

