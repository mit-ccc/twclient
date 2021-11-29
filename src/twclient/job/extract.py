'''
Jobs which extract data from the database.
'''

import csv
import logging

from abc import abstractmethod

import sqlalchemy as sa
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

    def run(self):
        # both of these are no-ops if targets == []
        self.resolve_targets()
        self._load_targets_to_stg()

        with ut.smart_open(self.outfile, mode='wt') as fle:
            writer = csv.DictWriter(fle, self.columns)
            writer.writeheader()

            for row in self.query():
                writer.writerow(dict(zip(self.columns, row)))

    def _load_targets_to_stg(self):
        ids = list(set(self.users))
        ids = ut.grouper(self.users, 5000)  # just a default batch size

        # Clear the stg table. This is much, much faster than .delete() /
        # DELETE FROM <tbl>, but not transactional on many DBs.
        md.StgUser.__table__.drop(self.session.get_bind())
        md.StgUser.__table__.create(self.session.get_bind())

        n_items = 0
        for ind, batch in enumerate(ids):
            msg = 'Loading extract target IDs batch {1}, cumulative {2}'
            msg = msg.format(ind + 1, n_items)
            logger.debug(msg)

            rows = {'user_id': t for t in batch}
            self.session.bulk_insert_mappings(md.StgFollow, rows)

            n_items += len(batch)

        return n_items


class ExtractFollowGraphJob(ExtractJob):
    columns = ['source_user_id', 'target_user_id']

# tag = 'universe'
# tagged_users = session \
#     .query(md.UserTag.user_id) \
#     .join(md.Tag, md.Tag.tag_id == md.UserTag.tag_id) \
#     .filter(md.Tag.name == tag) \
#     .all()
# print(tagged_users)

    def query(self):
        ret = self.session \
            .query(md.Follow)

        if self.users:
            ret = ret \
                .join(
                    md.StgUser,
                    md.StgUser.user_id == md.Follow.source_user_id
                ) \
                .join(
                    md.StgUser,
                    md.StgUser.user_id == md.Follow.target_user_id
                ) \

        ret = ret \
            .filter_by(valid_end_dt=None) \
            .with_entities(
                md.Follow.source_user_id,
                md.Follow.target_user_id
            ) \
            .all()

        yield from ret


class ExtractMentionGraphJob(ExtractJob):
    columns = ['source_user_id', 'target_user_id', 'count']

    def query(self):
        ret = self.session \
            .query(
                md.Tweet.user_id,
                md.UserMention.mentioned_user_id,
                func.count()
            ) \
            .join(md.Tweet, md.Tweet.tweet_id == md.UserMention.tweet_id)

        if self.users:
            ret = ret \
                .join(
                    md.StgUser,
                    md.StgUser.user_id == md.Tweet.user_id
                ) \
                .join(
                    md.StgUser,
                    md.StgUser.user_id == md.UserMention.mentioned_user_id
                ) \

        ret = ret \
            .group_by(md.Tweet.user_id, md.UserMention.mentioned_user_id) \
            .all()

        yield from ret


class ExtractRetweetGraphJob(ExtractJob):
    columns = ['source_user_id', 'target_user_id', 'count']

    def query(self):
        pass


class ExtractReplyGraphJob(ExtractJob):
    columns = ['source_user_id', 'target_user_id', 'count']

    def query(self):
        pass


class ExtractQuoteGraphJob(ExtractJob):
    columns = ['source_user_id', 'target_user_id', 'count']

    def query(self):
        pass


class ExtractTweetsJob(ExtractJob):
    columns = []

    def query(self):
        pass


class ExtractUserInfoJob(ExtractJob):
    columns = []

    def query(self):
        pass


class ExtractMutualFollowersJob(ExtractJob):
    columns = ['user_id1', 'user_id2', 'mutual_followers']

    def query(self):
        pass


class ExtractMutualFriendsJob(ExtractJob):
    columns = ['user_id1', 'user_id2', 'mutual_friends']

    def query(self):
        pass
