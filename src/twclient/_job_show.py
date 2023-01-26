'''
Jobs for printing information to the screen.
'''

import json
import logging

from ._job_base import ApiJob

from ._utils import export

logger = logging.getLogger(__name__)


# this is just a stub to placate the linter; the @export decorator adds
# objects to __all__ so that whether an object is included is noted next to it
__all__ = []

@export
class RateLimitStatusJob(ApiJob):
    '''
    Check the rate limits for the API keys in the config file.

    This job pulls the rate limit status for each key in the config file and
    prints it to stdout in json format. The job filters by default to only the
    API endpoints we use but can be told to show all of them.
    '''

    def __init__(self, **kwargs):
        full = kwargs.pop('full', False)
        consumer_key = kwargs.pop('consumer_key', None)

        super().__init__(**kwargs)

        self.full = full
        self.consumer_key = consumer_key

    def run(self):
        status = next(self.api.rate_limit_status())

        if not self.full:
            endpoints = ['/application/rate_limit_status', '/followers/ids',
                         '/friends/ids', '/users/lookup', '/lists/show',
                         '/lists/members', '/statuses/user_timeline']

            short = {}
            for key, resp in status.items():
                short[key] = {}

                for endpoint in endpoints:
                    _, grp, _ = endpoint.split('/')
                    short[key][endpoint] = resp['resources'][grp][endpoint]

            status = short

        status = json.dumps(status, indent=4)
        print(status)
