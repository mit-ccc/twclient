'''
Jobs which create, apply or delete user tags.
'''

import logging

from ._job_base import DatabaseJob, TargetJob
from .error import BadTagError
from .models import Tag
from ._utils import export

logger = logging.getLogger(__name__)


# this is just a stub to placate the linter; the @export decorator adds
# objects to __all__ so that whether an object is included is noted next to it
__all__ = []

@export
class TagJob(DatabaseJob):
    '''
    A job which uses user tags.

    A TagJob is a class which requires a user tag. It ensures that the database
    schema version is correct, and leaves other logic for subclasses.

    Parameters
    ----------
    tag : str
        The name of a user tag.

    Attributes
    ----------
    tag : str
        The parameter passed to __init__.
    '''

    def __init__(self, **kwargs):
        try:
            tag = kwargs.pop('tag')
        except KeyError as exc:
            raise ValueError('Must provide tag argument') from exc

        super().__init__(**kwargs)

        self.tag = tag

        self.ensure_schema_version()


@export
class CreateTagJob(TagJob):
    '''
    Create a user tag.

    This job creates a new user tag. If the tag already exists, nothing is done
    and no error is raised. The tag is not applied to any users. (See
    ApplyTagJob for that.)
    '''

    def run(self):
        self.get_or_create(Tag, name=self.tag)

        self.session.commit()


@export
class DeleteTagJob(TagJob):
    '''
    Delete a user tag.

    This job deletes a user tag. If the tag does not exist, nothing is done and
    no error is raised. Any existing assignments of the tag to users are also
    deleted.
    '''

    def run(self):
        tag = self.session.query(Tag).filter_by(name=self.tag).one_or_none()

        if tag:
            # DELETE is slow on many databases, but we're assuming none of
            # these lists are especially large - a few thousand rows, tops.
            # follow graph jobs have at least potentially really large data
            # and need to rely on DROP TABLE / CREATE TABLE (see below).
            self.session.delete(tag)

            self.session.commit()


@export
class ApplyTagJob(TagJob, TargetJob):
    '''
    Apply a user tag to a set of users.

    This job applies an existing user tag to a set of users. If the tag does
    not exist, error.BadTagError is raised. (Use CreateTagJob to create a new
    tag.) The targets are resolved to users with ``resolve_mode == 'skip'``
    (i.e., any requested users which do not exist in the database are not
    looked up from the Twitter API). If any users were not successfully
    resolved, error.BadTargetError is raised unless the allow_missing_targets
    parameter is True. Otherwise, any users which were successfully resolved
    from the targets are given the tag. In particular, if no users were
    successfully resolved and allow_missing_users is True, nothing is done and
    no error is raised. The entire job is run as one transaction; if anything
    goes wrong, no tags are applied.
    '''

    resolve_mode = 'skip'

    def run(self):
        self.resolve_targets()

        tag = self.session.query(Tag).filter_by(name=self.tag).one_or_none()

        if not tag:
            msg = f'Tag {self.tag} does not exist'
            raise BadTagError(message=msg, tag=tag)

        for user in self.users:
            user.tags.append(tag)

        self.session.commit()
