'''
A command to extract data from the database.
'''

import logging

from ..job import extract as ej
from . import command as cmd

logger = logging.getLogger(__name__)


class ExtractCommand(cmd.DatabaseCommand, cmd.TargetCommand):
    '''
    A command which extracts data from the database.

    This command and its subcommands run various sql queries against the
    database to extract useful pieces of data. Examples include the follow
    graph over all loaded users or only certain users, other tweet-derived
    graphs, or all user tweets.

    Parameters
    ----------
    outfile : str
        The file to write the extract to (default stdout).

    Attributes
    ----------
    outfile : str
        The parameter passed to __init__.
    '''

    targets_required = False

    def __init__(self, **kwargs):
        outfile = kwargs.pop('outfile', '-')

        super().__init__(**kwargs)

        self.outfile = outfile

    subcommand_to_job = {
        'follow-graph': ej.ExtractFollowGraphJob,
        'mention-graph': ej.ExtractMentionGraphJob,
        'retweet-graph': ej.ExtractRetweetGraphJob,
        'reply-graph': ej.ExtractReplyGraphJob,
        'quote-graph': ej.ExtractQuoteGraphJob,
        'tweets': ej.ExtractTweetsJob,
        'user-info': ej.ExtractUserInfoJob,
        'mutual-followers': ej.ExtractMutualFollowersJob,
        'mutual-friends': ej.ExtractMutualFriendsJob
    }

    @property
    def job_args(self):
        return {
            'engine': self.engine,

            'outfile': self.outfile,
            'targets': self.targets
        }
