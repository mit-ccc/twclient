'''
Jobs which extract data from the database.
'''

import csv
import logging
import collections as cl

from abc import abstractmethod

from sqlalchemy.sql.expression import func

from .job import DatabaseJob, TargetJob
from .. import _utils as ut
from .. import models as md

logger = logging.getLogger(__name__)


# This isn't a great way to handle these warnings, but sqlalchemy is so dynamic
# that most attribute accesses aren't resolved until runtime
# pylint: disable=no-member


class ExtractJob(TargetJob, DatabaseJob):
    resolve_mode = 'skip'  # bail out if requested targets are missing

    def __init__(self, **kwargs):
        outfile = kwargs.pop('outfile', '-')

        super().__init__(**kwargs)

        self.outfile = outfile

    @abstractmethod  # Job inherits from ABC
    def query(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def columns(self):
        raise NotImplementedError()

    def results(self):
        for row in self.query():
            yield dict(zip(self.columns, row))

    def run(self):
        self.resolve_targets()  # does nothing if targets == []

        with ut.smart_open(self.outfile, mode='wt') as fle:
            writer = csv.DictWriter(fle, self.columns)
            writer.writeheader()

            res = self.results()
            writer.writerows(res)


class ExtractFollowGraphJob(ExtractJob):
    columns = ['source_user_id', 'target_user_id']

    def query(self):
        yield from self.session \
            .query(md.Follow) \
            .filter_by(valid_end_dt=None) \
            .with_entities(
                md.Follow.source_user_id,
                md.Follow.target_user_id
            ) \
            .all()


class ExtractMentionGraphJob(ExtractJob):
    pass


class ExtractRetweetGraphJob(ExtractJob):
    pass


class ExtractReplyGraphJob(ExtractJob):
    pass


class ExtractQuoteGraphJob(ExtractJob):
    pass


class ExtractTweetsJob(ExtractJob):
    pass


class ExtractUserInfoJob(ExtractJob):
    pass


class ExtractMutualFollowersJob(ExtractJob):
    pass


class ExtractMutualFriendsJob(ExtractJob):
    pass

# tag = 'universe'
# tagged_users = session \
#     .query(md.UserTag.user_id) \
#     .join(md.Tag, md.Tag.tag_id == md.UserTag.tag_id) \
#     .filter(md.Tag.name == tag) \
#     .all()
# print(tagged_users)

# fg = self.session \
#     .query(md.Follow) \
#     .filter_by(valid_end_dt=None) \
#     .all()
# print(len(fg))
# print(fg[0])
#
# fg = [(r.source_user_id, r.target_user_id) for r in fg]
# print(len(fg))
# print(fg[0])

# mg = session \
#     .query(md.Tweet.user_id, md.UserMention.mentioned_user_id, func.count()) \
#     .join(md.Tweet, md.Tweet.tweet_id == md.UserMention.tweet_id) \
#     .group_by(md.Tweet.user_id, md.UserMention.mentioned_user_id) \
#     .all()
# print(len(mg))
# print(mg[0])

