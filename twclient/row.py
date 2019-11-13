import json
import logging

from abc import ABC, abstractmethod

fmt = '%(asctime)s : %(module)s : %(levelname)s : %(message)s'
logging.basicConfig(format=fmt, level=logging.INFO)
logger = logging.getLogger(__name__)

##
## Rows and Rowsets
## These classes encapsulate data points (and sets of data points)
## to load, and information about how to load them
##

class Rowset(object):
    def __init__(self, **kwargs):
        try:
            rows = kwargs.pop('rows')
        except KeyError:
            raise ValueError("Must provide rows")

        try:
            cls = kwargs.pop('cls')
        except KeyError:
            raise ValueError("Must provide cls")

        super(Rowset, self).__init__(**kwargs)

        self.rows = rows
        self.cls = cls

    @classmethod
    def from_records(cls, rowcls, records):
        return cls(rows=(rowcls(**x) for x in records), cls=rowcls)

    def as_records(self):
        yield from (row.as_record() for row in self.rows)

    @property
    def table(self):
        return self.cls.table

    @property
    def columns(self):
        return sorted(self.cls.column_type_map.keys())

    @property
    def column_types(self):
        return [self.cls.column_type_map[x] for x in self.columns]

class Row(ABC):
    def __init__(self, **kwargs):
        try:
            assert set(kwargs.keys()) <= set(self.column_type_map.keys())
        except AssertionError:
            raise ValueError("Keyword args must be a subset of allowed columns")

        try:
            assert set(self.not_null_columns) <= set(kwargs.keys())
        except AssertionError:
            raise ValueEror("Required keyword args not provided")

        super(Row, self).__init__()

        # we need to remove the nul character from strings if present
        # or databases object
        self._data = {
            k : v.replace('\00', '') if isinstance(v, str) else v
            for k, v in kwargs.items()
        }

    def __getitem__(self, i):
        if i in self._data.keys():
            return self._data[i]
        elif i in self.optional_columns:
            return self.column_default_map[i]
        else:
            raise KeyError(i)

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return str(self._data)

    @property
    @abstractmethod
    def table(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def column_type_map(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def column_default_map(self):
        raise NotImplementedError()

    @classmethod
    def from_tweepy(cls, obj):
        raise NotImplementedError()

    @property
    def columns(self):
        return sorted(self.column_type_map.keys())

    @property
    def optional_columns(self):
        return sorted(self.column_default_map.keys())

    @property
    def not_null_columns(self):
        return list(set(self.columns) - set(self.optional_columns))

    @property
    def column_types(self):
        return [self.column_type_map[x] for x in self.columns]

    @property
    def values(self):
        return [self[x] for x in self.columns]

    def as_record(self):
        return dict(zip(self.columns, self.values))

class UserRow(Row):
    table = 'user'

    column_type_map = {
        'user_id': 'bigint',
        'api_response': 'jsonb',
        'screen_name': 'varchar(256)',
        'account_create_dt': 'timestamptz',
        'protected': 'boolean',
        'verified': 'boolean',
        'name': 'text',
        'description': 'text',
        'location': 'text',
        'url': 'text'
    }

    column_default_map = {
        'api_response': None,
        'screen_name': None,
        'account_create_dt': None,
        'protected': None,
        'verified': None,
        'name': None,
        'description': None,
        'location': None,
        'url': None
    }

    @classmethod
    def from_tweepy(cls, obj):
        # As above we have to remove NUL bytes - they can't go in DB text fields
        api_response = json.dumps(obj._json)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'user_id': obj.id,
            'screen_name': obj.screen_name,
            'api_response': api_response # NOTE is this public API?
        }

        extra_fields = {
            'account_create_dt': 'created_at',
            'protected': 'protected',
            'verified': 'verified',
            'name': 'name',
            'description': 'description',
            'location': 'location',
            'url': 'url'
        }

        for t, s in extra_fields.items():
            if hasattr(obj, s):
                args[t] = getattr(obj, s)

        return cls(**args)

class UserTagRow(Row):
    table = 'user_tag'

    column_type_map = {
        'user_id': 'bigint',
        'tag': 'text'
    }

    column_default_map = {}

class TweetTagRow(Row):
    table = 'tweet_tag'

    column_type_map = {
        'user_id': 'bigint',
        'tag': 'text'
    }

    column_default_map = {}

class MentionRow(Row):
    table = 'mention'

    column_type_map = {
        'tweet_id': 'bigint',
        'mentioned_user_id': 'bigint'
    }

    column_default_map = {}

class FollowFetchRow(Row):
    table = 'follow_fetch'

    column_type_map = {
        'is_followers': 'boolean',
        'is_friends': 'boolean',
        'user_id': 'bigint'
    }

    column_default_map = {}

class FollowRow(Row):
    table = 'follow'

    column_type_map = {
        'follow_fetch_id': 'bigint',
        'source_user_id': 'bigint',
        'target_user_id': 'bigint'
    }

    column_default_map = {}

class TweetRow(Row):
    table = 'tweet'

    column_type_map = {
        'tweet_id': 'bigint',
        'user_id': 'bigint',
        'content': 'text',
        'api_response': 'jsonb',
        'tweet_create_dt': 'timestamptz',
        'lang': 'varchar(8)',
        'source': 'text',
        'truncated': 'boolean',
        'retweeted_status_id': 'bigint',
        'retweeted_status_content': 'text',
        'quoted_status_id': 'bigint',
        'quoted_status_content': 'text',
        'in_reply_to_user_id': 'bigint',
        'in_reply_to_screen_name': 'varchar(256)',
        'retweet_count': 'int',
        'favorite_count': 'int'
    }

    column_default_map = {
        'lang': None,
        'source': None,
        'truncated': None,
        'retweeted_status_id': None,
        'retweeted_status_content': None,
        'quoted_status_id': None,
        'quoted_status_content': None,
        'in_reply_to_user_id': None,
        'in_reply_to_screen_name': None,
        'retweet_count': None,
        'favorite_count': None
    }

    @classmethod
    def from_tweepy(cls, obj):
        # As above we have to remove NUL bytes - they can't go in DB text fields
        api_response = json.dumps(obj._json)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'tweet_id': obj.id,
            'user_id': obj.user.id,
            'api_response': api_response, # NOTE is this public API?
            'tweet_create_dt': obj.created_at
        }

        if hasattr(obj, 'full_text'):
            args['content'] = obj.full_text
        else:
            args['content'] = obj.text

        # commented out fields are handled specially below
        extra_fields = [
            'lang',
            'source',
            'truncated',
            # 'retweeted_status_id',
            # 'retweeted_status_content',
            'quoted_status_id'
            # 'quoted_status_content',
            'in_reply_to_user_id',
            'in_reply_to_screen_name',
            'retweet_count',
            'favorite_count',
        ]

        for t in extra_fields:
            if hasattr(obj, t):
                args[t] = getattr(obj, t)

        if hasattr(obj, 'quoted_status'):
            if hasattr(obj.quoted_status, 'full_text'):
                args['quoted_status_content'] = obj.quoted_status.full_text
            else:
                args['quoted_status_content'] = obj.quoted_status.text

        if hasattr(obj, 'retweeted_status'):
            args['retweeted_status_id'] = obj.retweeted_status.id

        if hasattr(obj, 'retweeted_status'):
            args['retweeted_status_content'] = obj.retweeted_status.id

        if hasattr(obj, 'retweeted_status'):
            # From the Twitter docs: "Note that while native retweets may have
            # their toplevel text property shortened, the original text will be
            # available under the retweeted_status object and the truncated
            # parameter will be set to the value of the original status (in most
            # cases, false)."
            if hasattr(obj.retweeted_status, 'full_text'):
                args['content'] = obj.retweeted_status.full_text
            else:
                args['content'] = obj.retweeted_status.text

        return cls(**args)

