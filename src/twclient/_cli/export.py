'''
A command to export data from the database.
'''

import logging

from .._job_export import (
    ExportFollowGraphJob,
    ExportMentionGraphJob,
    ExportRetweetGraphJob,
    ExportReplyGraphJob,
    ExportQuoteGraphJob,
    ExportTweetsJob,
    ExportUserInfoJob,
    ExportMutualFollowersJob,
    ExportMutualFriendsJob
)
from . import command as cmd

logger = logging.getLogger(__name__)


class ExportCommand(cmd.DatabaseCommand, cmd.TargetCommand):
    '''
    A command which exports data from the database.

    This command and its subcommands run various sql queries against the
    database to export useful pieces of data. Examples include the follow
    graph over all loaded users or only certain users, other tweet-derived
    graphs, or all user tweets.

    Parameters
    ----------
    outfile : str
        The file to write the export to (default stdout).

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
        'follow-graph': ExportFollowGraphJob,
        'mention-graph': ExportMentionGraphJob,
        'retweet-graph': ExportRetweetGraphJob,
        'reply-graph': ExportReplyGraphJob,
        'quote-graph': ExportQuoteGraphJob,
        'tweets': ExportTweetsJob,
        'user-info': ExportUserInfoJob,
        'mutual-followers': ExportMutualFollowersJob,
        'mutual-friends': ExportMutualFriendsJob
    }

    @property
    def job_args(self):
        return {
            'engine': self.engine,

            'outfile': self.outfile,
            'targets': self.targets,
            'allow_missing_targets': self.allow_missing_targets
        }
