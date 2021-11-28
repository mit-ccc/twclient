'''
Subcommands which use the Twitter API.
'''

import logging

from ..job import api_job as aj
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
        'ratelimit': aj.RateLimitStatusJob
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


class FetchCommand(cmd.ApiCommand, cmd.TargetCommand, cmd.DatabaseCommand):
    '''
    The command to fetch new data from Twitter.

    This class represents the fetch command to load new data from Twitter.
    Subcommands include "users", "friends", "followers", and "tweets", which
    load what their names indicate.

    Note that the load_batch_size setting is not used for loading user rows,
    but only for friends, followers and tweets.

    Parameters
    ----------
    since_timestamp : float
        Used only for loading tweets. Ignore (i.e., don't load) any tweets
        older than the time indicated by this Unix timestamp.

    max_tweets : int
        Stop loading after this many tweets. If more than this many tweets
        would be returned otherwise, the extras will not be fetched from the
        Twitter API to minimize usage of rate-limited API calls.

    old_tweets : bool
        If there are already tweets loaded for a given user in the database,
        should we fetch all tweets anyway (if True) or restrict to tweets with
        IDs higher than the maximum of the loaded tweets (if False, default)?
        Tweet IDs are sequential, so higher tweet IDs mean more recent tweets.
        The default minimizes loading time. Passing True may help recover if
        data was deleted or an initial fetch for a user employed max_tweets or
        since_timestamp.

    Attributes
    ----------
    since_timestamp : float
        The parameter passed to __init__.

    max_tweets : int
        The parameter passed to __init__.

    old_tweets : bool
        The parameter passed to __init__.
    '''

    subcommand_to_job = {
        'users': aj.UserInfoJob,
        'friends': aj.FriendsJob,
        'followers': aj.FollowersJob,
        'tweets': aj.TweetsJob
    }

    def __init__(self, **kwargs):
        # tweet-specific arguments
        since_timestamp = kwargs.pop('since_timestamp', None)
        max_tweets = kwargs.pop('max_tweets', None)
        old_tweets = kwargs.pop('old_tweets', None)

        super().__init__(**kwargs)

        if self.subcommand != 'tweets':
            if since_timestamp or max_tweets or old_tweets:
                raise ValueError('since_timestamp, max_tweets and old_tweets '
                                 'are only valid with subcommand = "tweets"')

        self.since_timestamp = since_timestamp
        self.max_tweets = max_tweets
        self.old_tweets = old_tweets

    @property
    def job_args(self):
        args = {
            'engine': self.engine,
            'api': self.api,
            'targets': self.targets,
            'allow_missing_targets': self.allow_missing_targets,
            'allow_api_errors': self.allow_api_errors,
            'load_batch_size': self.load_batch_size
        }

        if self.subcommand == 'tweets':
            args['since_timestamp'] = self.since_timestamp
            args['max_tweets'] = self.max_tweets
            args['old_tweets'] = self.old_tweets

        return args
