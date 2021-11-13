'''
A high-level analytics-focused command line client for the Twitter API
'''

__version__ = '0.2.0'

from . import error

from .authpool import AuthPoolAPI
from .twitter_api import TwitterApi

from . import job, target
