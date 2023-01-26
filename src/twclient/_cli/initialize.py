'''
A command to (re-)initialize the database.
'''

import logging

from .._job_initialize import InitializeJob
from . import command as cmd

logger = logging.getLogger(__name__)


class InitializeCommand(cmd.DatabaseCommand):
    '''
    The command to (re-)initialize the database schema.

    WARNING! This command drops all data in the database. If not backed up
    elsewhere, it will be lost. The InitializeCommand applies the schema
    defined in the models module against the selected database profile. Any
    existing data is dropped.

    Parameters
    ----------
    yes : bool
        Must be True for anything to be done. The default is False, in which
        case a warning message is emitted on the logger and no changes are
        made. This parameter corresponds to the -y command-line flag.

    Attributes
    ----------
    yes : bool
        The parameter passed to __init__.
    '''

    subcommand_to_job = {
        'initialize': InitializeJob
    }

    def __init__(self, **kwargs):
        yes = kwargs.pop('yes', False)

        # this doesn't actually take a subcommand, just a hack to
        # make it work with the same machinery as the others
        kwargs['subcommand'] = 'initialize'

        super().__init__(**kwargs)

        if not yes:
            self.error("WARNING: This command will drop the Twitter data "
                       "tables and delete all data! If you want to "
                       "proceed, rerun with -y / --yes.")
        else:
            logger.warning('Recreating schema and dropping existing data')

    @property
    def job_args(self):
        return {
            'engine': self.engine
        }
