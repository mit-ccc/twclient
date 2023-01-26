'''
A high-level analytics-focused command line client for the Twitter API.
'''

from ._version import __version__

from . import authpool
from . import config
from . import error
from . import job
from . import models
from . import target
from . import twitter_api

__all__ = [
    'authpool',
    'config',
    'error',
    'job',
    'models',
    'target',
    'twitter_api'
]
