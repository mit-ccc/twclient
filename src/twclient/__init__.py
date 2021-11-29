'''
A high-level analytics-focused command line client for the Twitter API.
'''

__version__ = '0.2.0'

from . import authpool
from . import config
from . import error
from . import job
from . import models
from . import target
from . import twitter_api

from .authpool import AuthPoolAPI
from .config import Config
from .twitter_api import TwitterApi

_modules = [authpool, config, error, job, models, target, twitter_api]

__all__ = []
for module in _modules:
    if hasattr(module, '__all__'):
        __all__ += getattr(module, '__all__')
