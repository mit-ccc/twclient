'''
Jobs which initialize the database.
'''

import logging

from .job import DatabaseJob

from .. import __version__
from .. import models as md

logger = logging.getLogger(__name__)


class InitializeJob(DatabaseJob):
    '''
    A job which initializes the selected database and sets up the schema.

    WARNING! This job will drop all data in the selected database! This job
    (re-)initializes the selected database and applies the schema to it. The
    version of the creating package will also be stored to help future versions
    with migrations and compatibility checks.
    '''

    def run(self):
        md.reinitialize(self.engine)
        self.session.add(md.SchemaVersion(version=__version__))
        self.session.commit()
