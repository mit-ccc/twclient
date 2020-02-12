# FIXME option for copy/insert loading method

import sys
import random
import logging

from importlib.resources import open_text
from abc import ABC, abstractmethod

import tweepy
import psycopg2

from psycopg2 import sql

import twclient.error as err
import twclient.utils as ut

from twclient.row import Rowset
from twclient.row import UserRow, TweetRow, UserTagRow, TweetTagRow
from twclient.row import FollowRow, FollowFetchRow, MentionRow
from twclient.authpool import AuthPoolAPI

logger = logging.getLogger(__name__)

##
## Job classes
## These encapsulate different types of loading jobs, including
## the details of interacting with the database and Twitter API
##

class DatabaseJob(ABC):
    def __init__(self, **kwargs):
        dsn = kwargs.pop('dsn', None)
        socket = kwargs.pop('socket', None)
        conn = kwargs.pop('conn', None)
        schema = kwargs.pop('schema', 'twitter')

        assert ut.coalesce(dsn, socket, conn) is not None

        super(DatabaseJob, self).__init__(**kwargs)

        self.dsn = dsn
        self.socket = socket
        self.schema = schema

        if conn is not None:
            self.conn = conn
            self._conn_owner = False
        else:
            self.conn = self._new_db_connection()
            self._conn_owner = True

    def _new_db_connection(self):
        if self.dsn is not None:
            conn_args = {'dsn': self.dsn}
        else:
            conn_args = {'host': self.socket}

        return psycopg2.connect(**conn_args)

    @abstractmethod
    def run(self):
        raise NotImplementedError()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if self._conn_owner:
            self.conn.close()

    # WARNING drops the schema and deletes all data!
    def db_initialize(self):
        schema = open_text('twclient.sql', 'schema.sql').read().strip()

        with self.conn.cursor() as cur:
            cur.execute(schema)

    def commit(self):
        logger.debug('Committing')

        self.conn.commit()

    @staticmethod
    def _copy_stmt(table, cols, sep=',', schema=None):
        query = [sql.SQL('copy')]

        if schema is not None:
            query += [sql.Identifier(schema), sql.SQL('.')]

        query += [
            sql.Identifier(table),

            sql.SQL('('),
            sql.SQL(', ').join(sql.Identifier(n) for n in cols),
            sql.SQL(')'),

            sql.SQL('from stdin'),

            sql.SQL('csv'),
            sql.SQL('header'),
            sql.SQL('delimiter'), sql.Literal(sep)
        ]

        return query

    @staticmethod
    def _insert_stmt(table, cols, payload, schema=None, returning=[],
                     conflict='merge', conflict_constraint=['id']):
        assert conflict in ('raise', 'merge', 'skip')

        query = [sql.SQL('insert into')]

        if schema is not None:
            query += [sql.Identifier(schema), sql.SQL('.')]

        query += [
            sql.Identifier(table), sql.SQL('as tbl'),

            sql.SQL('('),
            sql.SQL(', ').join(sql.Identifier(n) for n in cols),
            sql.SQL(')')
        ]

        query += payload

        update_cols = list(set(cols) - set(conflict_constraint))

        if conflict == 'skip' or len(update_cols) == 0:
            query += [
                sql.SQL('on conflict do nothing')
            ]
        elif conflict == 'merge':
            query += [
                sql.SQL('on conflict'),

                sql.SQL('('),
                sql.SQL(', ').join(sql.Identifier(n) for n in conflict_constraint),
                sql.SQL(')'),

                sql.SQL('do update set'),

                sql.SQL(', ').join(
                    sql.SQL(' ').join([
                        sql.Identifier(n), sql.SQL('='),
                        sql.SQL('coalesce'), sql.SQL('('),
                        sql.Identifier('excluded'), sql.SQL('.'),
                        sql.Identifier(n), sql.SQL(','),
                        sql.Identifier('tbl'), sql.SQL('.'),
                        sql.Identifier(n), sql.SQL(')')
                    ]) for n in update_cols
                )
            ]
        else:
            pass # raise (on unique constraint violation) is the default

        if len(returning) > 0:
            query += [
                sql.SQL('returning'),
                sql.SQL(', ').join(sql.Identifier(n) for n in returning),
            ]

        return query

    @staticmethod
    def _create_tmp_tbl_stmt(table, cols, types=None):
        if types is None:
            types = ['text' for c in cols]

        query = [
            sql.SQL('create local temporary table'), sql.Identifier(table),
            sql.SQL('('),

            sql.SQL(', ').join(
                sql.SQL(' ').join([
                    sql.Identifier(n),
                    sql.SQL(t)
                ]) for n, t in zip(cols, types)
            ),

            sql.SQL(')'),
        ]

        return query

    def db_load_data_copy(self, data, returning=[], conflict='raise',
                          conflict_constraint=['id']):
        logger.debug('Loading data via COPY')

        if len(returning) > 0:
            raise ValueError("can only use INSERT INTO ... RETURNING ... " +
                             "from db_load_data_insert")

        if data.table is None: # no rows to load
            return None

        ##
        ## First, create a temporary table for the data
        ##

        # not necessarily thread-safe
        tmptbl = data.table + '_load_tmp_' + next(ut.unique_names)

        query = self._create_tmp_tbl_stmt(table=tmptbl, cols=data.columns,
                                          types=data.column_types)
        query = sql.Composed(query).join(' ').as_string(self.conn)

        with self.conn.cursor() as cur:
            cur.execute(query)

        ##
        ## Second, copy the data to the temp table
        ##

        query = self._copy_stmt(table=tmptbl, cols=data.columns)
        query = sql.Composed(query).join(' ').as_string(self.conn)

        with ut.write_to_tempfile(data=data.as_records(), fieldnames=data.columns) as f:
            with self.conn.cursor() as cur:
                cur.copy_expert(query, f)

        ##
        ## Third, run the insert into the permanent table
        ##

        payload = [
            sql.SQL('select'),

            sql.SQL(', ').join(sql.Identifier(n) for n in data.columns),

            sql.SQL('from'), sql.Identifier(tmptbl)
        ]

        query = self._insert_stmt(
            table=data.table, cols=data.columns, payload=payload,
            schema=self.schema, returning=returning, conflict=conflict,
            conflict_constraint=conflict_constraint
        )
        query = sql.Composed(query).join(' ').as_string(self.conn)

        with self.conn.cursor() as cur:
            cur.execute(query)

    def db_load_data_insert(self, data, returning=[], conflict='raise',
                            conflict_constraint=['id']):
        logger.debug('Loading data via INSERT')

        assert not (data.table is None and len(returning) > 0)

        if data.table is None:
            return []

        payload = [
            sql.SQL('values'),

            sql.SQL('('),
            sql.SQL(', ').join(sql.Placeholder(n) for n in data.columns),
            sql.SQL(')')
        ]

        query = self._insert_stmt(
            table=data.table, cols=data.columns, payload=payload,
            schema=self.schema, returning=returning, conflict=conflict,
            conflict_constraint=conflict_constraint
        )
        query = sql.Composed(query).join(' ').as_string(self.conn)

        res = []
        with self.conn.cursor() as cur:
            if len(returning) > 0:
                # executemany doesn't return values, so we need to
                # do them one at a time
                for row in data.as_records():
                    cur.execute(query, row)
                    res += cur.fetchall()
            else:
                cur.executemany(query, data.as_records())

        return res

    def db_load_data(self, data, how='copy', returning=[],
                     conflict='raise', conflict_constraint=['id']):
        assert how in ('copy', 'insert')
        assert conflict in ('raise', 'merge', 'skip')
        assert not (how == 'copy' and len(returning) > 0)

        args = {
            'data': data,
            'returning': returning,
            'conflict': conflict,
            'conflict_constraint': conflict_constraint
        }

        if how == 'copy':
            self.db_load_data_copy(**args) # always None
            return [] # for consistency of return type with insert
        else: # how == 'insert'
            return self.db_load_data_insert(**args)

    def db_get_data(self, query, parameters=None, flatten=False):
        with self.conn.cursor() as cur:
            cur.execute(query, parameters)

            res = cur.fetchall()

        if all([len(x) == 1 for x in res]) and flatten:
            return [x[0] for x in res]
        else:
            return res

    def user_ids_for_tag(self, tag):
        ret = self.db_get_data("""
        select
            u.user_id
        from twitter.user u
            inner join twitter.user_tag ut using(user_id)
        where
            ut.tag = %s;
        """, (tag,))

        return [x[0] for x in ret]

    def user_id_exists(self, user_id):
        ret = self.db_get_data("""
        select
            count(*) > 0
        from twitter.user u
        where
            u.user_id = %s;
        """, (user_id,))

        return ret[0][0]

    def user_ids_exist(self, user_ids):
        # NOTE could be more efficient...
        return [self.user_id_exists(u) for u in user_ids]

    def max_tweet_ids_for_user_ids(self, user_ids):
        query = """
        select
            u.user_id,
            max(t.tweet_id)
        from (values {0}) u(user_id)
            left join twitter.tweet t on t.user_id = u.user_id::bigint
        group by 1;
        """.format(','.join(['(%s)' for u in user_ids]))

        ret = self.db_get_data(query, user_ids)
        ret = [row for uid, row in sorted(zip(user_ids, ret))]

        return ret

    def user_id_for_screen_name(self, screen_name):
        ret = self.db_get_data("""
        select
            u.user_id
        from twitter.user u
        where
            lower(u.screen_name) = lower(%s)
        order by u.modified_dt desc
        limit 1;
        """, (screen_name,))

        return ret[0][0] if len(ret) > 0 else None

    def user_ids_for_screen_names(self, screen_names):
        # NOTE could be more efficient...
        return [self.user_id_for_screen_name(s) for s in screen_names]

    def resolve_user_spec(self, user_spec):
        logger.debug('Resolving user_spec {0}'.format(user_spec))

        assert user_spec in ('all', 'missing_user_info',
                             'missing_friends', 'missing_followers',
                             'missing_tweets')

        if user_spec == 'all':
            return self._get_all_user_ids()
        elif user_spec == 'missing_user_info':
            return self._get_user_ids_missing_info()
        elif user_spec == 'missing_friends':
            return self._get_user_ids_missing_friends()
        elif user_spec == 'missing_followers':
            return self._get_user_ids_missing_followers()
        else: # user_spec == 'missing_tweets'
            return self._get_user_ids_missing_tweets()

    def _get_user_ids_all(self):
        return self.db_get_data("""
        select
            u.user_id
        from twitter.user u;
        """, flatten=True)

    def _get_user_ids_missing_info(self):
        return self.db_get_data("""
        select
            u.user_id
        from twitter.user u
        where
            u.api_response is null;
        """, flatten=True)

    def _get_user_ids_missing_friends(self):
        return self.db_get_data("""
        select
            u.user_id
        from twitter.user u
        where
            not exists
            (
                select
                    1
                from twitter.follow_fetch ff
                where
                    ff.is_friends and
                    ff.user_id = u.user_id
            );
        """, flatten=True)

    def _get_user_ids_missing_followers(self):
        return self.db_get_data("""
        select
            u.user_id
        from twitter.user u
        where
            not exists
            (
                select
                    1
                from twitter.follow_fetch ff
                where
                    ff.is_followers and
                    ff.user_id = u.user_id
            );
        """, flatten=True)

    def _get_user_ids_missing_tweets(self):
        return self.db_get_data("""
        select
            u.user_id
        from twitter.user u
        where
            not exists
            (
                select
                    1
                from twitter.tweet t
                where
                    t.user_id = u.user_id
            );
        """, flatten=True)

class InitializeJob(DatabaseJob):
    def run(self):
        self.db_initialize()

class StatsJob(DatabaseJob):
    def run(self):
        queries = [
            # how many users loaded?
            # how many have been fully populated?
            """
            select
                count(*) as users,
                coalesce(sum((u.api_response is not null)::int), 0) as populated
            from twitter.user u;
            """,

            # how many tweets loaded?
            # how many users have tweets loaded?
            """
            select
                count(*) as tweets,
                count(distinct user_id) as users
            from twitter.tweet;
            """,

            # how many mentioning tweets?
            # how many have mentions?
            """
            select
                count(*),
                count(distinct mentioned_user_id) as users
            from twitter.mention;
            """,

            # how many graph edges?
            # how many have ever had followers recorded?
            # how many have ever had friends recorded?
            """
            select
                count(*) as edges,
                count(distinct source_user_id) as sources,
                count(distinct target_user_id) as targets
            from twitter.follow;
            """
        ]

        names = [
            'users_loaded',
            'users_populated',
            'tweets_loaded',
            'users_with_tweets',
            'mentions_loaded',
            'users_mentioned',
            'follow_graph_edges',
            'users_with_friends',
            'users_with_followers'
        ]

        vals = [self.db_get_data(query) for query in queries]
        vals = [x for y in vals for x in y] # flatten to list of tuples
        vals = [x for y in vals for x in y] # flatten to list of values

        return dict(zip(names, vals))

class ApiJob(DatabaseJob):
    def __init__(self, **kwargs):
        try:
            auths = kwargs.pop('auths')
        except KeyError:
            raise ValueError("auths argument is required")

        user_tag = kwargs.pop('user_tag', None)
        load_batch_size = kwargs.pop('load_batch_size', None)
        abort_on_bad_targets = kwargs.pop('abort_on_bad_targets', False)
        transaction = kwargs.pop('transaction', False)

        user_ids = kwargs.pop('user_ids', None)
        screen_names = kwargs.pop('screen_names', None)
        user_spec = kwargs.pop('user_spec', None)
        twitter_lists = kwargs.pop('twitter_lists', None)
        select_tag = kwargs.pop('select_tag', None)

        # exactly one operating mode at once
        assert sum([
            twitter_lists is not None,
            screen_names is not None,
            ut.coalesce(user_ids, user_spec, select_tag) is not None
        ]) == 1

        super(ApiJob, self).__init__(**kwargs)

        if screen_names is not None:
            screen_names = list(set(screen_names))

        if twitter_lists is not None:
            twitter_lists = list(set(twitter_lists))

        if user_spec is not None:
            if user_ids is not None:
                user_ids += self.resolve_user_spec(user_spec)
            else:
                user_ids = self.resolve_user_spec(user_spec)

        if select_tag is not None:
            if user_ids is not None:
                user_ids += self.user_ids_for_tag(select_tag)
            else:
                user_ids = self.user_ids_for_tag(select_tag)

        if user_ids is not None:
            user_ids = list(set(user_ids))

        if user_ids is not None:
            self.targets = user_ids
            self.target_type = 'user_ids'
        elif screen_names is not None:
            self.targets = screen_names
            self.target_type = 'screen_names'
        else: # twitter_lists is not None
            self.targets = twitter_lists
            self.target_type = 'twitter_lists'

        # Make partial loads more statistically useful
        random.shuffle(self.targets)

        self.auths = auths
        self.user_tag = user_tag
        self.load_batch_size = load_batch_size
        self.abort_on_bad_targets = abort_on_bad_targets
        self.transaction = transaction

        self.api = AuthPoolAPI(auths=auths, wait_on_rate_limit=True)

    def make_api_call(self, method, cursor=False, max_items=None, **kwargs):
        msg = 'API call: {0} with params {1}, cursor {2}'
        logger.debug(msg.format(method, kwargs, cursor))

        try:
            assert not (cursor and max_items is not None)
        except AssertionError:
            raise ValueError("max_items only available with cursor=True")

        twargs = dict({'method': method}, **kwargs)

        try:
            if cursor and max_items is not None:
                ret = tweepy.Cursor(**twargs).items(max_items)
            elif cursor:
                ret = tweepy.Cursor(**twargs).items()
            else:
                ret = method(**kwargs)

            yield from ret
        except err.TWClientError as e:
            if isinstance(e, err.ProtectedUserError):
                msg = 'Ignoring protected user in call to method {0} ' \
                      'with arguments {1}'
                msg = msg.format(method, kwargs)
                logger.warning(msg)
            elif isinstance(e, err.BadUserError):
                if self.abort_on_bad_targets:
                    raise
                else:
                    msg = 'Ignoring bad user in call to method {0} ' \
                          'with arguments {1}'
                    msg = msg.format(method, kwargs)
                    logger.warning(msg)
            else:
                message = e.message
                api_code = e.api_code
                if e.response is not None:
                    http_code = e.response.status_code
                else:
                    http_code = None

                msg = 'Error returned by Twitter API: API code {0}, HTTP ' \
                      'status code {1}, message {2}'
                msg = msg.format(api_code, http_code, message)

                logger.debug(msg, exc_info=True)

                raise

    @staticmethod
    def mentions_for_tweet(tweet):
        mentions, users = [], []

        if hasattr(tweet, 'entities'):
            if 'user_mentions' in tweet.entities.keys():
                for m in tweet.entities['user_mentions']:
                    urow = {'user_id': m['id']}

                    if 'screen_name' in m.keys():
                        urow['screen_name'] = m['screen_name']

                    if 'name' in m.keys():
                        urow['name'] = m['name']

                    users += [urow]

                    mentions += [{
                        'tweet_id': tweet.id,
                        'mentioned_user_id': m['id']
                    }]

        return mentions, users

    def mentions_for_tweets(self, tweets):
        # process tweets
        dat = [self.mentions_for_tweet(t) for t in tweets]

        mentions = [x[0] for x in dat]
        mentions = [x for y in mentions for x in y]
        mentions = [dict(t) for t in {tuple(d.items()) for d in mentions}]

        # extract users
        users = [x[1] for x in dat]
        users = [x for y in users for x in y]
        users = [dict(t) for t in {tuple(d.items()) for d in users}]

        return mentions, users

    def load_mentions(self, tweets):
        logger.debug('Loading mentions')

        mentions, mentioned_users = self.mentions_for_tweets(tweets)
        mentioned_ids = list(set([x['user_id'] for x in mentioned_users]))

        self.sync_users(targets=mentioned_ids, target_type='user_ids',
                        full=self.full, new=True, commit=False)

        self.db_load_data(
            data=Rowset.from_records(MentionRow, mentions),
            conflict='merge',
            conflict_constraint=['tweet_id', 'mentioned_user_id']
        )

    def load_tweets(self, tweets, load_mentions=True):
        logger.debug('Loading tweets')

        tweets = [t for t in tweets] # no generators, need >1 reference

        rows = [TweetRow.from_tweepy(u) for u in tweets]
        tweet_ids = [t.as_record()['tweet_id'] for t in rows]
        twrows = Rowset(rows=rows, cls=TweetRow)

        self.db_load_data(twrows, conflict='merge',
                          conflict_constraint=['tweet_id'])

        if self.tweet_tag is not None:
            ttrows = Rowset(rows=(
                TweetTagRow(tweet_id=t, tag=self.tweet_tag)
                for t in tweet_ids
            ), cls=TweetTagRow)

            self.db_load_data(ttrows, conflict='merge',
                              conflict_constraint=['user_id', 'tag'])

        if load_mentions:
            self.load_mentions(tweets)

    def load_follow_fetch(self, user_id, direction):
        msg = 'Loading follow_fetch row for user_id {0}, direction {1}'
        logger.debug(msg.format(user_id, direction))

        assert direction in ('followers', 'friends')

        ffr = FollowFetchRow(
            is_followers = (direction == 'followers'),
            is_friends = (direction == 'friends'),
            user_id = user_id
        )

        ff_id = self.db_load_data(Rowset(rows=[ffr], cls=FollowFetchRow),
                                  how='insert', returning=['follow_fetch_id'],
                                  conflict='raise')[0][0]

        return ff_id

    # edges are assumed to be (source, target)
    def load_follow_edges(self, edges, follow_fetch_id):
        logger.debug('Loading follow edges')

        edges = [e for e in edges]

        user_ids = list(set([x for y in edges for x in y]))
        self.sync_users(targets=user_ids, target_type='user_ids',
                        full=self.full, new=True, commit=False)

        rows = Rowset(rows=(
            FollowRow(
                follow_fetch_id=follow_fetch_id,
                source_user_id=source,
                target_user_id=target
            ) for source, target in edges
        ), cls=FollowRow)

        cols = ['follow_fetch_id', 'source_user_id', 'target_user_id']
        self.db_load_data(rows, conflict='merge', conflict_constraint=cols)

    ## Most API methods will encounter and need to handle new user
    ## objects, not just the jobs that only load user info
    def load_users(self, targets, kind):
        logger.debug('Loading {0} users'.format(kind))

        assert kind in ('users', 'user_ids')

        if kind == 'users':
            rows = [UserRow.from_tweepy(u) for u in targets]
        else:
            rows = [UserRow(user_id=u) for u in targets]

        user_ids = [u.as_record()['user_id'] for u in rows]

        urows = Rowset(rows=rows, cls=UserRow)
        self.db_load_data(urows, conflict='merge',
                          conflict_constraint=['user_id'])

        if self.user_tag is not None:
            logger.debug('Loading user tags: {0}'.format(self.user_tag))

            tag_rows = Rowset(rows=(
                UserTagRow(tag=self.user_tag, user_id=u)
                for u in user_ids
            ), cls=UserTagRow)

            self.db_load_data(tag_rows, conflict='merge',
                              conflict_constraint=['user_id', 'tag'])

    def user_objects_for(self, objs, kind):
        logger.debug('Fetching user objects for {0}'.format(kind))

        assert kind in ('user_ids', 'screen_names', 'twitter_lists')

        if kind == 'twitter_lists':
            for i, obj in enumerate(objs):
                logger.info('Running list {1}: {2}'.format(i, obj))

                owner_screen_name, slug = obj.split('/')

                yield from self.make_api_call(
                    method=self.api.list_members,
                    cursor=True,
                    slug=slug,
                    owner_screen_name=owner_screen_name
                )
        else:
            for i, grp in enumerate(ut.grouper(objs, 100)): # max 100 per call
                logger.info('Running {0} batch {1}'.format(kind, i))

                ret = self.make_api_call(self.api.lookup_users, **{kind: grp})

                j = 0
                for hobj in ret:
                    yield hobj
                    j += 1

                if j < len(grp):
                    if self.abort_on_bad_targets:
                        msg = 'Missing users: {0} not returned by users/lookup'
                        raise err.BadUserError(msg.format(len(grp) - j))
                    else:
                        msg = 'Missing users: {0} not returned by users/lookup'
                        logger.warning(msg.format(len(grp) - j))

                yield from ret

    def user_objects_for_lists(self, twitter_lists):
        yield from self.user_objects_for(twitter_lists, kind='twitter_lists')

    def user_objects_for_ids(self, user_ids, new=False):
        if not new:
            objs = user_ids
        else:
            objs = (
                user_id
                for user_id in user_ids
                if not self.user_id_exists(user_id)
            )
        yield from self.user_objects_for(objs=objs, kind='user_ids')

    def user_objects_for_screen_names(self, screen_names, new=False):
        if not new:
            objs = screen_names
        else:
            objs = (
                screen_name
                for screen_name in screen_names
                if self.user_id_for_screen_name(screen_name) is None
            )

        yield from self.user_objects_for(objs=objs, kind='screen_names')

    def tweet_objects_for(self, objs, kind, since_ids=None, max_tweets=None,
                          since_timestamp=None):
        msg = 'Loading tweet objects with ' +\
        'since_ids={0}, max_tweets={1}, since_timestamp={2}'
        logger.debug(msg.format(since_ids, max_tweets, since_timestamp))

        assert kind in ('user_ids', 'screen_names', 'twitter_lists')

        for i, obj in enumerate(objs):
            if since_ids is not None:
                since_id = since_ids[i]
            else:
                since_id = None

            twargs = {
                'count': 200, # the max in one call
                'tweet_mode': 'extended', # don't truncate tweet text
                'include_rts': True,
                'since_id': since_id
            }

            if kind == 'twitter_lists':
                method = self.api.list_timeline

                owner_screen_name, slug = twitter_list.split('/')
                twargs = dict(twargs, **{
                    'slug': slug,
                    'owner_screen_name': owner_screen_name
                })
            else:
                method = self.api.user_timeline

                param = 'user_id' if kind == 'user_ids' else 'screen_name'
                twargs = dict(twargs, **{param: obj})

            tweets = self.make_api_call(method, cursor=True,
                                        max_items=max_tweets, **twargs)

            yield from (
                tweet
                for tweet in tweets
                if (since_timestamp is None) or \
                   (tweet.created_at.timestamp() >= since_timestamp)
            )

    def tweet_objects_for_lists(self, twitter_lists, **kwargs):
        yield from self.tweet_objects_for(objs=twitter_lists,
                                          kind='twitter_list', **kwargs)

    def tweet_objects_for_ids(self, user_ids, **kwargs):
        yield from self.tweet_objects_for(objs=user_ids,
                                          kind='user_ids', **kwargs)

    def tweet_objects_for_screen_names(self, screen_names, **kwargs):
        yield from self.tweet_objects_for(objs=screen_names,
                                          kind='screen_names', **kwargs)

    def follow_objects_for(self, objs, kind, direction):
        logger.debug('Loading {0}'.format(direction))

        assert kind in ('user_ids', 'screen_names')
        assert direction in ('followers', 'friends')

        for obj in objs:
            param = ('user_id' if kind == 'user_ids' else 'screen_name')

            if direction == 'followers':
                method = self.api.followers_ids
            if direction == 'friends':
                method = self.api.friends_ids

            edges = self.make_api_call(method, cursor=True, **{param: obj})

            for item in edges:
                if direction == 'followers':
                    yield [item, obj]
                else: # direction == 'friends'
                    yield [obj, item]

    def follow_objects_for_ids(self, user_ids, **kwargs):
        yield from self.follow_objects_for(objs=user_ids,
                                           kind='user_ids', **kwargs)

    def follow_objects_for_screen_names(self, screen_names, **kwargs):
        yield from self.follow_objects_for(objs=screen_names,
                                           kind='screen_names', **kwargs)

    # Given a set of targets, which may be screen names, user ids or
    # users in a Twitter list and which may not exist in the twitter.user
    # table yet, we want to a) resolve them all to user ids
    # and b) ensure they all exist in the twitter.user table.
    def sync_users(self, targets, target_type, new=True, full=False,
                   commit=False):
        msg = 'Syncing {0} users, new={1}, full={2}, commit={3}'
        logger.debug(msg.format(target_type, new, full, commit))

        # full doesn't matter in the first two cases: we have to fetch
        # every user from the twitter API anyway because all we have
        # is a screen name
        if target_type == 'twitter_lists':
            # "new" is ignored here: we have to fetch them all from the
            # list members endpoint anyway to even learn who they are
            kind = 'users'
            users = self.user_objects_for_lists(self.targets)
        elif target_type == 'screen_names':
            kind = 'users'
            users = self.user_objects_for_screen_names(targets, new=new)
        elif full:
            kind = 'users'
            users = self.user_objects_for_ids(targets, new=new)
        else:
            kind = 'user_ids'
            users = targets

        n_items = 0
        for i, batch in enumerate(ut.grouper(users, self.load_batch_size)):
            msg = 'Running user batch {0}, cumulative users {1}'
            msg = msg.format(i, n_items)
            logger.debug(msg)

            self.load_users(targets=batch, kind=kind)

            n_items += len(batch)

            if commit:
                self.commit()

class UserInfoJob(ApiJob):
    def run(self):
        # NOTE self.targets isn't a generator, so we can safely take its len()
        msg = 'Loading info for {0} new or existing users'
        msg = msg.format(len(self.targets))
        logger.info(msg)

        self.sync_users(targets=self.targets, target_type=self.target_type,
                        new=False, full=True, commit=(not self.transaction))

        if self.transaction:
            self.commit()

class FollowJob(ApiJob):
    def __init__(self, **kwargs):
        direction = kwargs.pop('direction', 'followers')
        full = kwargs.pop('full', False)

        assert full is not None
        assert direction in ('followers', 'friends')

        super(FollowJob, self).__init__(**kwargs)

        assert self.target_type != 'twitter_lists'

        self.direction = direction
        self.full = full

    # What we're doing here:
    # 1) load user to twitter.user if not already there
    # 2) load the follow_fetch row, get its id, ff_id
    # 3) loop over pages of graph neighbors:
        # 3a) get the users from twitter
        # 3b) if requested, hydrate the users via users/lookup
        # 3c) load the users to twitter.user, merging if present
        # 3d) load the follow rows to twitter.follow, using ff_id
    def run(self):
        self.sync_users(targets=self.targets, target_type=self.target_type,
                        new=True, full=self.full, commit=(not self.transaction))

        if self.target_type == 'user_ids':
            user_ids = self.targets
        if self.target_type == 'screen_names':
            user_ids = self.user_ids_for_screen_names(self.targets)

        # there may be very very many users returned, so let's process
        # them incrementally rather than building one giant list
        n_items = 0
        for i, user_id in enumerate(user_ids):
            msg = 'Processing user {0} ({1} / {2})'
            logger.debug(msg.format(user_id, i, len(user_ids)))

            ff_id = self.load_follow_fetch(user_id=user_id,
                                           direction=self.direction)

            edges = self.follow_objects_for(objs=[user_id], kind='user_ids',
                                            direction=self.direction)
            edges = ut.grouper(edges, self.load_batch_size)

            for j, batch in enumerate(edges):
                msg = 'Running user {0} ({1}/{2}) batch {3}, cumulative {4}'
                msg = msg.format(user_id, i, len(user_ids), j, n_items)
                logger.info(msg)

                self.load_follow_edges(edges=batch, follow_fetch_id=ff_id)
                n_items += len(batch)

            # NOTE: it's safe to commit here even if make_api_call caught a
            # BadUserError, because in that case it just won't return any rows
            # and the loop above is a no-op
            if not self.transaction:
                self.commit()

        if self.transaction:
            self.commit()

class TweetsJob(ApiJob):
    def __init__(self, **kwargs):
        since_timestamp = kwargs.pop('since_timestamp', None)
        max_tweets = kwargs.pop('max_tweets', None)
        old_tweets = kwargs.pop('old_tweets', False)
        tweet_tag = kwargs.pop('tweet_tag', None)
        full = kwargs.pop('full', False)

        super(TweetsJob, self).__init__(**kwargs)

        # NOTE this could be implemented but has not been
        if self.target_type == 'twitter_lists':
            raise NotImplementedError()

        self.since_timestamp = since_timestamp
        self.max_tweets = max_tweets
        self.old_tweets = old_tweets
        self.tweet_tag = tweet_tag
        self.full = full

    def run(self):
        self.sync_users(targets=self.targets, target_type=self.target_type,
                        new=True, full=self.full, commit=(not self.transaction))

        if self.target_type == 'user_ids':
            user_ids = self.targets
        if self.target_type == 'screen_names':
            user_ids = self.user_ids_for_screen_names(self.targets)

        if self.old_tweets:
            logger.debug('Allowing old tweets')
            since_ids = [None for x in user_ids]
        else:
            logger.debug('Skipping old tweets')
            since_ids = self.max_tweet_ids_for_user_ids(user_ids)
            since_ids = [x[1] for x in since_ids]

        n_items = 0
        for i, (user_id, since_id) in enumerate(zip(user_ids, since_ids)):
            msg = 'Processing user {0} ({1} / {2})'
            logger.debug(msg.format(user_id, i, len(user_ids)))

            tweets = self.tweet_objects_for_ids(**{
                'user_ids': [user_id],
                'since_ids': [since_id],
                'max_tweets': self.max_tweets,
                'since_timestamp': self.since_timestamp
            })

            for j, batch in enumerate(ut.grouper(tweets, self.load_batch_size)):
                msg = 'Running user {0} ({1} / {2}) batch {3}, cumulative {4}'
                logger.info(msg.format(user_id, i, len(user_ids), j, n_items))

                self.load_tweets(batch, load_mentions=True)
                n_items += len(batch)

            # NOTE: it's safe to commit here even if make_api_call caught a
            # BadUserError, because in that case it just won't return any rows
            # and the loop above is a no-op
            if not self.transaction:
                self.commit()

        if self.transaction:
            self.commit()

