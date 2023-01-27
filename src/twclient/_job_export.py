'''
Jobs which export data from the database.
'''

import csv
import logging

from abc import abstractmethod

import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.sql.expression import func

from ._job_base import DatabaseJob, TargetJob
from ._utils import smart_open, grouper, export
from .models import Follow, StgUser, Tweet, Url, UserData, UserMention

logger = logging.getLogger(__name__)


# this is just a stub to placate the linter; the @export decorator adds
# objects to __all__ so that whether an object is included is noted next to it
__all__ = []

@export
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

        with smart_open(self.outfile, mode='wt') as fle:
            writer = csv.DictWriter(fle, self.columns)
            writer.writeheader()

            for row in self.query():
                writer.writerow(dict(zip(self.columns, row)))

    def _load_targets_to_stg(self):
        ids = list(set(self.users))
        ids = grouper(self.users, 5000)  # just a default batch size

        StgUser.clear_fast(self.session)

        n_items = 0
        for ind, batch in enumerate(ids):
            msg = 'Loading export target IDs batch {0}, cumulative {1}'
            msg = msg.format(ind + 1, n_items)
            logger.debug(msg)

            rows = ({'user_id': t.user_id} for t in batch)
            self.session.bulk_insert_mappings(StgUser, rows)

            n_items += len(batch)

        return n_items


@export
class ExportFollowGraphJob(ExportJob):
    '''
    Export the follow graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user follows the
    target user. There is one row per edge (i.e., per pair of users with a
    following relationship).

    If targets are specified, return only the follow graph on the users they
    describe; otherwise, return the entire graph.
    '''

    columns = ['source_user_id', 'target_user_id']

    def query(self):
        ret = self.session \
            .query(Follow.source_user_id, Follow.target_user_id)

        if self.users:
            su1 = sa.orm.aliased(StgUser)
            su2 = sa.orm.aliased(StgUser)

            ret = ret \
                .join(su1, su1.user_id == Follow.source_user_id) \
                .join(su2, su2.user_id == Follow.target_user_id) \

        ret = ret \
            .filter(Follow.valid_end_dt.is_(None))

        yield from ret


@export
class ExportMentionGraphJob(ExportJob):
    '''
    Export the mention graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user has mentioned
    the target user. The third column ``num_mentions`` gives the number of
    mentions. There is one row per edge (i.e., per pair of users with a mention
    relationship).

    If targets are specified, return the mention graph only on the users they
    specify; otherwise, return the entire graph.
    '''

    columns = ['source_user_id', 'target_user_id', 'num_mentions']

    def query(self):
        ret = self.session \
            .query(
                Tweet.user_id,
                UserMention.mentioned_user_id,
                func.count()
            ) \
            .join(Tweet, Tweet.tweet_id == UserMention.tweet_id)

        if self.users:
            su1 = sa.orm.aliased(StgUser)
            su2 = sa.orm.aliased(StgUser)

            ret = ret \
                .join(su1, su1.user_id == Tweet.user_id) \
                .join(su2, su2.user_id == UserMention.mentioned_user_id) \

        ret = ret \
            .group_by(Tweet.user_id, UserMention.mentioned_user_id)

        yield from ret


@export
class ExportReplyGraphJob(ExportJob):
    '''
    Export the reply graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user has replied to
    the target user. The third column ``num_mentions`` gives the number of
    mentions. There is one row per edge (i.e., per pair of users with a reply
    relationship).

    If targets are specified, return the reply graph only on the users they
    specify; otherwise, return the entire graph.
    '''

    columns = ['source_user_id', 'target_user_id', 'num_replies']

    def query(self):
        ret = self.session \
            .query(
                Tweet.user_id,
                Tweet.in_reply_to_user_id,
                func.count()
            )

        if self.users:
            su1 = sa.orm.aliased(StgUser)
            su2 = sa.orm.aliased(StgUser)

            ret = ret \
                .join(su1, su1.user_id == Tweet.user_id) \
                .join(su2, su2.user_id == Tweet.in_reply_to_user_id)

        ret = ret \
            .filter(Tweet.in_reply_to_user_id.isnot(None)) \
            .group_by(Tweet.user_id, Tweet.in_reply_to_user_id)

        yield from ret


@export
class ExportRetweetGraphJob(ExportJob):
    '''
    Export the retweet graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user has retweeted
    the target user. The third column ``num_mentions`` gives the number of
    mentions. There is one row per edge (i.e., per pair of users with a retweet
    relationship).

    If targets are specified, return the retweet graph only on the users they
    specify; otherwise, return the entire graph.
    '''

    columns = ['source_user_id', 'target_user_id', 'num_retweets']

    def query(self):
        tws = sa.orm.aliased(Tweet)
        twt = sa.orm.aliased(Tweet)

        ret = self.session \
            .query(tws.user_id, twt.user_id, func.count()) \
            .join(twt, twt.tweet_id == tws.retweeted_status_id)

        if self.users:
            su1 = sa.orm.aliased(StgUser)
            su2 = sa.orm.aliased(StgUser)

            ret = ret \
                .join(su1, su1.user_id == twt.user_id) \
                .join(su2, su2.user_id == tws.user_id)

        ret = ret \
            .group_by(tws.user_id, twt.user_id)

        yield from ret


@export
class ExportQuoteGraphJob(ExportJob):
    '''
    Export the quote graph.

    This export is a graph in edgelist format, with an edge from
    ``source_user_id`` to ``target_user_id`` if the source user has
    quote-tweeted the target user. The third column ``num_mentions`` gives the
    number of mentions. There is one row per edge (i.e., per pair of users with
    a quote-tweet relationship).

    If targets are specified, return the quote graph only on the users they
    specify; otherwise, return the entire graph.
    '''

    columns = ['source_user_id', 'target_user_id', 'num_quotes']

    def query(self):
        tws = sa.orm.aliased(Tweet)
        twt = sa.orm.aliased(Tweet)

        ret = self.session \
            .query(tws.user_id, twt.user_id, func.count()) \
            .join(twt, twt.tweet_id == tws.quoted_status_id)

        if self.users:
            su1 = sa.orm.aliased(StgUser)
            su2 = sa.orm.aliased(StgUser)

            ret = ret \
                .join(su1, su1.user_id == twt.user_id) \
                .join(su2, su2.user_id == tws.user_id)

        ret = ret \
            .group_by(tws.user_id, twt.user_id)

        yield from ret


@export
class ExportTweetsJob(ExportJob):
    '''
    Export the set of user tweets.

    This export includes all tweets for either all users or a particular set of
    targets. Various relevant fields are included, including in particular the
    text of any retweeted/quoted/replied-to status and a recoded version of the
    client from which the tweet was posted. There is one row per tweet.

    If targets are specified, return only tweets by the users they specify;
    otherwise, return all tweets. Note that because we receive and store full
    tweet objects for quote tweets and retweets, and users can RT or QT any
    other user, not just ones whose tweets were fetched, "all tweets" may
    include some tweets by users whose tweets weren't explicitly fetched.
    '''

    columns = ['tweet_id', 'user_id', 'content', 'retweeted_status_content',
               'quoted_status_content', 'in_reply_to_status_content',
               'is_retweet', 'is_reply', 'is_quote', 'create_dt', 'lang',
               'retweet_count', 'favorite_count', 'source_collapsed']

    def query(self):
        twt = sa.orm.aliased(Tweet)
        twr = sa.orm.aliased(Tweet)
        twq = sa.orm.aliased(Tweet)
        twp = sa.orm.aliased(Tweet)

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

                sa.case({
                    'Twitter for iPhone': 'iPhone',
                    'Twitter for Android': 'Android',
                    'Twitter Web App': 'Web',
                    'Twitter Web Client': 'Web',
                    'TweetDeck': 'Desktop'
                }, value=twt.source, else_='Other')
            ) \
            .join(twr, twr.tweet_id == twt.retweeted_status_id, isouter=True) \
            .join(twq, twq.tweet_id == twt.quoted_status_id, isouter=True) \
            .join(twp, twp.tweet_id == twt.in_reply_to_status_id, isouter=True)

        if self.users:
            ret = ret \
                .join(StgUser, StgUser.user_id == twt.user_id)

        yield from ret


@export
class ExportUserInfoJob(ExportJob):
    '''
    Export user-level information.

    This export includes user-level information. Besides the Twitter-assigned
    user ID, fields include such things as the profile URL and self-reported
    location, counts of friends, followers and list memberships, verified
    status, and other such user-specific fields. If a given user's data has
    been fetched more than once, only the most recent fetch will be used. There
    is one row per user.

    If targets are specified, only those users will be included in the export.
    If no targets are specified, the default is to return rows for all users
    who have been fetched with ``twitter fetch users`` (i.e., those with rows
    in the ``user_data`` table).
    '''

    columns = ['user_id', 'profile_url', 'friends_count', 'followers_count',
               'listed_count', 'screen_name', 'location', 'display_name',
               'description', 'protected', 'verified', 'account_create_dt',
               'recorded_tweets_all_time', 'first_tweet_dt', 'last_tweet_dt',
               'android_user', 'ios_user', 'desktop_user', 'business_app_user']

    def query(self):  # pylint: disable=too-many-locals
        if self.users:
            eligibles = StgUser

            # we have to refer to subquery columns with subquery.c.column
            # rather than table.column as for tables, so this function
            # abstracts away which to use (rather than wrapping StgUser in a
            # subquery which might have performance implications on e.g. MySQL)
            def access(obj, name):
                return getattr(obj, name)
        else:
            eligibles = self.session \
                .query(UserData.user_id) \
                .group_by(UserData.user_id) \
                .subquery()

            def access(obj, name):
                return getattr(getattr(obj, 'c'), name)

        elt = sa.orm.aliased(eligibles)
        twt = sa.orm.aliased(Tweet)
        tweet_data = self.session \
            .query(
                access(elt, 'user_id').label('user_id'),
                func.count(twt.tweet_id).label('recorded_tweets_all_time'),
                func.min(twt.create_dt).label('first_tweet_dt'),
                func.max(twt.create_dt).label('last_tweet_dt'),
                func.max(
                    sa.case(*[
                        (twt.source.in_(['Twitter for Android']), 1)
                    ], else_=0)
                ).label('android_user'),
                func.max(
                    sa.case(*[
                        (twt.source.in_([
                            'Twitter for iPhone', 'Twitter for iPad', 'iOS',
                            'Tweetbot for iOS'
                        ]), 1)
                    ], else_=0)
                ).label('ios_user'),
                func.max(
                    sa.case(*[
                        (twt.source.in_([
                            'Twitter Web App', 'Twitter Web Client',
                            'TweetDeck', 'Twitter for Mac', 'Tweetbot for Mac'
                        ]), 1)
                    ], else_=0)
                ).label('desktop_user'),
                func.max(
                    sa.case(*[
                        (twt.source.in_([
                            'SocialFlow', 'Hootsuite', 'Hootsuite Inc.',
                            'Twitter Media Studio'
                        ]), 1)
                    ], else_=0)
                ).label('business_app_user')
            ) \
            .join(twt, access(elt, 'user_id') == twt.user_id) \
            .group_by(access(elt, 'user_id')) \
            .subquery()

        elu = sa.orm.aliased(eligibles)
        uda = sa.orm.aliased(UserData)
        url = sa.orm.aliased(Url)
        user_data_inner = self.session \
            .query(
                uda.user_id.label('user_id'),
                url.url.label('profile_url'),
                uda.friends_count.label('friends_count'),
                uda.followers_count.label('followers_count'),
                uda.listed_count.label('listed_count'),
                uda.screen_name.label('screen_name'),
                uda.location.label('location'),
                uda.display_name.label('display_name'),
                uda.description.label('description'),
                uda.protected.label('protected'),
                uda.verified.label('verified'),
                uda.create_dt.label('account_create_dt'),
                func.row_number().over(
                    partition_by=uda.user_id,
                    order_by=uda.insert_dt.desc()
                ).label('rn')
            ) \
            .join(elu, uda.user_id == access(elu, 'user_id')) \
            .join(url, url.url_id == uda.url_id, isouter=True) \
            .subquery()

        udi = sa.orm.aliased(user_data_inner)
        user_data = self.session \
            .query(udi) \
            .filter(udi.c.rn == 1) \
            .subquery()

        tda = sa.orm.aliased(tweet_data)
        uds = sa.orm.aliased(user_data)
        eli = sa.orm.aliased(eligibles)
        ret = self.session \
            .query(
                access(eli, 'user_id'),
                uds.c.profile_url.label('profile_url'),
                uds.c.friends_count.label('friends_count'),
                uds.c.followers_count.label('followers_count'),
                uds.c.listed_count.label('listed_count'),
                uds.c.screen_name.label('screen_name'),
                uds.c.location.label('location'),
                uds.c.display_name.label('display_name'),
                uds.c.description.label('description'),
                uds.c.protected.label('protected'),
                uds.c.verified.label('verified'),
                uds.c.account_create_dt.label('account_create_dt'),

                func.coalesce(tda.c.recorded_tweets_all_time, 0) \
                    .label('recorded_tweets_all_time'),
                tda.c.first_tweet_dt.label('first_tweet_dt'),
                tda.c.last_tweet_dt.label('last_tweet_dt'),
                tda.c.android_user.label('android_user'),
                tda.c.ios_user.label('ios_user'),
                tda.c.desktop_user.label('desktop_user'),
                tda.c.business_app_user.label('business_app_user')
            ) \
            .join(uds, uds.c.user_id == access(eli, 'user_id'), isouter=True) \
            .join(tda, tda.c.user_id == access(eli, 'user_id'), isouter=True)

        yield from ret


@export
class ExportMutualsJob(ExportJob):
    '''
    Compute mutual friends or followers counts for pairs of some set of users.
    '''

    @property
    def columns(self):
        columns = ['user_id1', 'user_id2']

        if self.direction == 'followers':
            columns += ['mutual_followers']
        else:
            columns += ['mutual_friends']

        return columns

    @property
    @abstractmethod
    def direction(self):
        '''
        The direction (friends or followers) of mutual counts to compute.
        '''

        raise NotImplementedError()

    def query(self):
        if self.direction == 'followers':
            select_col = 'source_user_id'
            filter_col = 'target_user_id'
        else:
            select_col = 'target_user_id'
            filter_col = 'source_user_id'

        if self.users:
            eligibles = StgUser

            def access(obj, name):
                return getattr(obj, name)
        else:
            eligibles = self.session \
                .query(UserData.user_id) \
                .group_by(UserData.user_id) \
                .subquery()

            def access(obj, name):
                return getattr(getattr(obj, 'c'), name)

        el1 = sa.orm.aliased(eligibles)
        el2 = sa.orm.aliased(eligibles)

        fo1 = sa.orm.aliased(Follow)
        mutuals1 = self.session \
            .query(getattr(fo1, select_col).label('source_user_id')) \
            .filter(
                fo1.valid_end_dt.is_(None),
                getattr(fo1, filter_col) == access(el1, 'user_id')
            ).correlate(el1)

        fo2 = sa.orm.aliased(Follow)
        mutuals2 = self.session \
            .query(getattr(fo2, select_col).label('source_user_id')) \
            .filter(
                fo2.valid_end_dt.is_(None),
                getattr(fo2, filter_col) == access(el2, 'user_id')
            ).correlate(el2)

        if self.session.bind.dialect.name == 'sqlite':
            # sqlite doesn't support INTERSECT ALL
            mutuals = mutuals1.intersect(mutuals2).subquery()
        else:
            mutuals = mutuals1.intersect_all(mutuals2).subquery()
        mutuals_count = sql.select(func.count()).select_from(mutuals).scalar_subquery()

        ret = self.session \
            .query(
                access(el1, 'user_id').label('user_id1'),
                access(el2, 'user_id').label('user_id2'),
                mutuals_count.label('mutual_followers')
            ) \
            .join(el1, access(el1, 'user_id') > access(el2, 'user_id')) \
            .group_by(
                access(el1, 'user_id'),
                access(el2, 'user_id')
            )

        yield from ret


@export
class ExportMutualFollowersJob(ExportMutualsJob):
    '''
    Export counts of mutual followers.

    This export includes counts of mutual followers between all pairs of users
    from a certain set of eligible users (exactly which set is discussed
    below). That is, if user A and user B are both included, there will be one
    row with a count of the number of users who follow both A and B. Note that
    you must have fetched followers of both A and B for the counts to be
    accurate: if either has not had followers fetched, there will be a row for
    the (A, B) pair but it will record 0 mutual followers. There is one row per
    pair of users in the set of eligible users (for all pairs).

    If targets are specified, the set of eligible users is restricted to only
    the users they describe. Otherwise, the default set of users is those who
    have been fetched with ``twitter fetch users`` (i.e., those with rows in
    the ``user_data`` table).
    '''

    direction = 'followers'


@export
class ExportMutualFriendsJob(ExportMutualsJob):
    '''
    Export counts of mutual friends.

    This export includes counts of mutual friends between all pairs of users
    from a certain set of eligible users (exactly which set is discussed
    below). That is, if user A and user B are both included, there will be one
    row with a count of the number of users who are followed by both A and B.
    Note that you must have fetched friends of both A and B for the counts to
    be accurate: if either has not had friends fetched, there will be a row for
    the (A, B) pair but it will record 0 mutual friends. There is one row per
    pair of users in the set of eligible users (for all pairs).

    If targets are specified, the set of eligible users is restricted to only
    the users they describe. Otherwise, the default set of users is those who
    have been fetched with ``twitter fetch users`` (i.e., those with rows in
    the ``user_data`` table).
    '''

    direction = 'friends'
