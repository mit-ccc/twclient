'''
Jobs which initialize the database.
'''

import logging

from ._job_base import DatabaseJob

from ._version import __version__
from .models import SchemaVersion, reinitialize
from ._utils import export

logger = logging.getLogger(__name__)


# this is just a stub to placate the linter; the @export decorator adds
# objects to __all__ so that whether an object is included is noted next to it
__all__ = []

@export
class InitializeJob(DatabaseJob):
    '''
    A job which initializes the selected database and sets up the schema.

    WARNING! This job will drop all data in the selected database! This job
    (re-)initializes the selected database and applies the schema to it. The
    version of the creating package will also be stored to help future versions
    with migrations and compatibility checks.
    '''

    def run(self):
        reinitialize(self.engine)
        self.session.add(SchemaVersion(version=__version__))
        self.session.commit()
