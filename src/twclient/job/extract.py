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
    '''
    '''

    resolve_mode = 'skip'  # bail out if requested targets are missing

    def __init__(self, **kwargs):
        outfile = kwargs.pop('outfile', '-')

        super().__init__(**kwargs)

        self.outfile = outfile

    @abstractmethod  # Job inherits from ABC
    def query(self):
        '''
        '''

        raise NotImplementedError()

    @property
    @abstractmethod
    def columns(self):
        '''
        '''

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
            msg = 'Loading extract target IDs batch {0}, cumulative {1}'
            msg = msg.format(ind + 1, n_items)
            logger.debug(msg)

            rows = ({'user_id': t.user_id} for t in batch)
            self.session.bulk_insert_mappings(md.StgUser, rows)

            n_items += len(batch)

        return n_items


class ExtractFollowGraphJob(ExtractJob):
    '''
    '''

    columns = ['source_user_id', 'target_user_id']

    def query(self):
        ret = self.session \
            .query(md.Follow)

        if self.users:
            su1 = sa.orm.aliased(md.StgUser)
            su2 = sa.orm.aliased(md.StgUser)

            ret = ret \
                .join(su1, su1.user_id == md.Follow.source_user_id) \
                .join(su2, su2.user_id == md.Follow.target_user_id) \

        ret = ret \
            .filter_by(valid_end_dt=None) \
            .with_entities(
                md.Follow.source_user_id,
                md.Follow.target_user_id
            ) \
            .all()

        yield from ret


class ExtractMentionGraphJob(ExtractJob):
    '''
    '''

    columns = ['source_user_id', 'target_user_id', 'num_mentions']

    def query(self):
        ret = self.session \
            .query(
                md.Tweet.user_id,
                md.UserMention.mentioned_user_id,
                func.count()
            ) \
            .join(md.Tweet, md.Tweet.tweet_id == md.UserMention.tweet_id)

        if self.users:
            su1 = sa.orm.aliased(md.StgUser)
            su2 = sa.orm.aliased(md.StgUser)

            ret = ret \
                .join(su1, su1.user_id == md.Tweet.user_id) \
                .join(su2, su2.user_id == md.UserMention.mentioned_user_id) \

        ret = ret \
            .group_by(md.Tweet.user_id, md.UserMention.mentioned_user_id) \
            .all()

        yield from ret


class ExtractReplyGraphJob(ExtractJob):
    '''
    '''

    columns = ['source_user_id', 'target_user_id', 'num_replies']

    def query(self):
        ret = self.session \
            .query(
                md.Tweet.user_id,
                md.Tweet.in_reply_to_user_id,
                func.count()
            )

        if self.users:
            su1 = sa.orm.aliased(md.StgUser)
            su2 = sa.orm.aliased(md.StgUser)

            ret = ret \
                .join(su1, su1.user_id == md.Tweet.user_id) \
                .join(su2, su2.user_id == md.Tweet.in_reply_to_user_id)

        ret = ret \
            .filter(md.Tweet.in_reply_to_user_id.isnot(None)) \
            .group_by(md.Tweet.user_id, md.Tweet.in_reply_to_user_id) \
            .all()

        yield from ret


class ExtractRetweetGraphJob(ExtractJob):
    '''
    '''

    columns = ['source_user_id', 'target_user_id', 'num_retweets']

    def query(self):
        tws = sa.orm.aliased(md.Tweet)
        twt = sa.orm.aliased(md.Tweet)

        ret = self.session \
            .query(tws.user_id, twt.user_id, func.count()) \
            .join(twt, twt.tweet_id == tws.retweeted_status_id)

        if self.users:
            su1 = sa.orm.aliased(md.StgUser)
            su2 = sa.orm.aliased(md.StgUser)

            ret = ret \
                .join(su1, su1.user_id == twt.user_id) \
                .join(su2, su2.user_id == tws.user_id)

        ret = ret \
            .group_by(tws.user_id, twt.user_id) \
            .all()

        yield from ret


class ExtractQuoteGraphJob(ExtractJob):
    '''
    '''

    columns = ['source_user_id', 'target_user_id', 'num_quotes']

    def query(self):
        tws = sa.orm.aliased(md.Tweet)
        twt = sa.orm.aliased(md.Tweet)

        ret = self.session \
            .query(tws.user_id, twt.user_id, func.count()) \
            .join(twt, twt.tweet_id == tws.quoted_status_id)

        if self.users:
            su1 = sa.orm.aliased(md.StgUser)
            su2 = sa.orm.aliased(md.StgUser)

            ret = ret \
                .join(su1, su1.user_id == twt.user_id) \
                .join(su2, su2.user_id == tws.user_id)

        ret = ret \
            .group_by(tws.user_id, twt.user_id) \
            .all()

        yield from ret


class ExtractTweetsJob(ExtractJob):
    '''
    '''

    columns = ['tweet_id', 'user_id', 'content', 'retweeted_status_content',
               'quoted_status_content', 'in_reply_to_status_content',
               'is_retweet', 'is_reply', 'is_quote', 'create_dt', 'lang',
               'retweet_count', 'favorite_count', 'source_collapsed']

    def query(self):
        twt = sa.orm.aliased(md.Tweet)
        twr = sa.orm.aliased(md.Tweet)
        twq = sa.orm.aliased(md.Tweet)
        twp = sa.orm.aliased(md.Tweet)

        ret = self.session \
            .query(
                twt.tweet_id,
                twt.user_id,

                twt.content,
                twr.content,
                twq.content,
                twp.content,

                twt.retweeted_status_id.isnot(None),
                twt.in_reply_to_status_id.isnot(None),
                twt.quoted_status_id.isnot(None),

                twt.create_dt,
                twt.lang,
                twt.retweet_count,
                twt.favorite_count,

                func.case(value=twt.source, whens={
                    'Twitter for iPhone': 'iPhone',
                    'Twitter for Android': 'Android',
                    'Twitter Web App': 'Web',
                    'Twitter Web Client': 'Web',
                    'TweetDeck': 'Desktop'
                }, else_='Other')
            ) \
            .join(twr, twr.tweet_id == twt.retweeted_status_id) \
            .join(twq, twq.tweet_id == twt.quoted_status_id) \
            .join(twp, twp.tweet_id == twt.in_reply_to_status_id)

        if self.users:
            ret = ret \
                .join(md.StgUser, md.StgUser.user_id == twt.user_id)

        yield from ret


class ExtractUserInfoJob(ExtractJob):
    '''
    '''

    columns = []

    def query(self):
        pass


class ExtractMutualFollowersJob(ExtractJob):
    '''
    '''

    columns = ['user_id1', 'user_id2', 'mutual_followers']

    def query(self):
        pass


class ExtractMutualFriendsJob(ExtractJob):
    '''
    '''

    columns = ['user_id1', 'user_id2', 'mutual_friends']

    def query(self):
        pass
