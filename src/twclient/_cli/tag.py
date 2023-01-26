'''
A command to work with user tags.
'''

import logging

from .._job_tag import (
    CreateTagJob,
    DeleteTagJob,
    ApplyTagJob
)
from . import command as cmd

logger = logging.getLogger(__name__)


class TagCommand(cmd.DatabaseCommand, cmd.TargetCommand):
    '''
    A command which manages user tags.

    A TagCommand manages (creates, deletes, or applies to users) the user tags
    that can group users together for easier selection of targets. Subcommands
    are "create", "delete" and "apply".

    Parameters
    ----------
    name : str
        The name of the tag to operate on.

    Attributes
    ----------
    name : str
        The parameter passed to __init__.
    '''

    subcommand_to_job = {
        'create': CreateTagJob,
        'delete': DeleteTagJob,
        'apply': ApplyTagJob
    }

    def __init__(self, **kwargs):
        try:
            name = kwargs.pop('name')
        except KeyError as exc:
            raise ValueError('Must provide name argument') from exc

        super().__init__(**kwargs)

        self.name = name

    @property
    def targets_required(self):
        '''
        This class attribute from the superclass is an instance property here.
        Because targets are needed only for the "apply" subcommand, it is True
        if self.subcommand == 'apply' and False otherwise.
        '''

        return self.subcommand == 'apply'

    @property
    def job_args(self):
        args = {
            'tag': self.name,
            'engine': self.engine,
        }

        if self.subcommand == 'apply':
            args['targets'] = self.targets
            args['allow_missing_targets'] = self.allow_missing_targets

        return args
