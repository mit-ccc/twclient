'''
A command to print data from the database to the screen.
'''

import logging

from .._job_show import RateLimitStatusJob
from . import command as cmd

logger = logging.getLogger(__name__)


# could easily be extended to show other things, inherit other cmd bases
class ShowCommand(cmd.ApiCommand):
    '''
    Print rate-limit status information for API keys.

    This command prints information about users, DBs API keys, etc. Currently
    the only implemented subcommand is ``rate-limit-status`` to show rate-limit
    status for all API keys stored in the config file (or only a particular
    one).

    Parameters
    ----------
    name : str or None
        The name of an API profile in the config file.

    consumer_key : str or None
        The consumer key of an API profile in the config file.

    full : boolean
        Whether to return the Twitter API's full response.

    Attributes
    ----------
    name : str or None
        The parameter passed to __init__.

    consumer_key : str or None
        The parameter passed to __init__.

    full : boolean
        The parameter passed to __init__.
    '''

    subcommand_to_job = {
        'ratelimit': RateLimitStatusJob
    }

    def __init__(self, **kwargs):
        name = kwargs.pop('name', None)
        consumer_key = kwargs.pop('consumer_key', None)
        full = kwargs.pop('full', False)

        try:
            assert name is None or consumer_key is None
        except AssertionError as exc:
            msg = 'Cannot provide both name and consumer_key'
            raise ValueError(msg) from exc

        super().__init__(**kwargs)

        self.name = name
        self.consumer_key = consumer_key
        self.full = full

    @property
    def job_args(self):
        ret = {
            'api': self.api,
            'full': self.full
        }

        # we check above that only one of these is provided
        consumer_key = self.consumer_key
        if self.name is not None:
            ind = self.config.api_profile_names.index(self.name)
            consumer_key = self.api.auths[ind].consumer_key
        ret['consumer_key'] = consumer_key

        return ret
