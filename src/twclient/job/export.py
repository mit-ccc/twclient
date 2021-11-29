'''
Jobs which export data from the database.
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


class ExportJob(TargetJob, DatabaseJob):
    '''
    A job exporting data from the database.

    This class represents a job which pulls an export of collected Twitter data
    from the database. Several subclasses are defined for particular kinds of
    commonly used exports. If targets are given, the exports are restricted to
    only those targets (but note that how to do this is export-specific and
    subclasses must implement it). The exports produced are CSV files with
    columns given by the ``columns`` property, in the order they appear there.

    Parameters
    ----------
    outfile : str
        The path to the file where we should write the export (default '-' for
        stdout).

    Attributes
    ----------
    outfile : str
        The parameter passed to __init__.
    '''

    resolve_mode = 'skip'  # bail out if requested targets are missing

    def __init__(self, **kwargs):
        outfile = kwargs.pop('outfile', '-')

        super().__init__(**kwargs)

        self.outfile = outfile

    @abstractmethod  # Job inherits from ABC
    def query(self):
        '''
        The sqlalchemy query returning rows to export.

        This method is the main piece of business logic for subclasses, which
        must implement it along with the ``columns`` property. It should return
        an iterable (or be a generator) of tuples, with the elements of each
        tuple assumed to be in the order specified by the ``columns`` property.
        '''

        raise NotImplementedError()

    @property
    @abstractmethod
    def columns(self):
        '''
        The list of column names for the resultset returned by the ``query``
        method.

        Subclasses must implement this property along with the ``query``
        method.
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
            msg = 'Loading export target IDs batch {0}, cumulative {1}'
            msg = msg.format(ind + 1, n_items)
            logger.debug(msg)

            rows = ({'user_id': t.user_id} for t in batch)
            self.session.bulk_insert_mappings(md.StgUser, rows)

            n_items += len(batch)

        return n_items


class ExportFollowGraphJob(ExportJob):
    '''
    Export the follow graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user follows the
    target user.
    '''

    columns = ['source_user_id', 'target_user_id']

    def query(self):
        ret = self.session \
            .query(md.Follow.source_user_id, md.Follow.target_user_id)

        if self.users:
            su1 = sa.orm.aliased(md.StgUser)
            su2 = sa.orm.aliased(md.StgUser)

            ret = ret \
                .join(su1, su1.user_id == md.Follow.source_user_id) \
                .join(su2, su2.user_id == md.Follow.target_user_id) \

        ret = ret \
            .filter_by(valid_end_dt=None) \
            .all()

        yield from ret


class ExportMentionGraphJob(ExportJob):
    '''
    Export the mention graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user has mentioned
    the target user. The third column ``num_mentions`` gives the number of
    mentions.
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


class ExportReplyGraphJob(ExportJob):
    '''
    Export the reply graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user has replied to
    the target user. The third column ``num_mentions`` gives the number of
    mentions.
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


class ExportRetweetGraphJob(ExportJob):
    '''
    Export the retweet graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user has retweeted
    the target user. The third column ``num_mentions`` gives the number of
    mentions.
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


class ExportQuoteGraphJob(ExportJob):
    '''
    Export the quote graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user has
    quote-tweeted the target user. The third column ``num_mentions`` gives the
    number of mentions.
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


class ExportTweetsJob(ExportJob):
    '''
    Export the set of user tweets.

    This export includes all tweets for either all users or a particular set of
    targets. Various relevant fields are included, including in particular the
    text of any retweeted/quoted/replied-to status and a recoded version of the
    client from which the tweet was posted.
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


class ExportUserInfoJob(ExportJob):
    '''
    '''

    columns = []

    def query(self):
        pass


class ExportMutualFollowersJob(ExportJob):
    '''
    '''

    columns = ['user_id1', 'user_id2', 'mutual_followers']

    def query(self):
        pass


class ExportMutualFriendsJob(ExportJob):
    '''
    '''

    columns = ['user_id1', 'user_id2', 'mutual_friends']

    def query(self):
        pass
