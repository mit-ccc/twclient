# FIXME weird update bug in UrlMention
# FIXME need to index tables:
#     o) for the FollowGraphJob load process
#     o) index FKs

# FIXME tweet media entity

import json
import logging

from abc import ABC, abstractmethod

import sqlalchemy as sa
import sqlalchemy.sql.functions as func

from sqlalchemy.types import Boolean, Integer, BigInteger, String, UnicodeText
from sqlalchemy.types import TIMESTAMP # recommended over DateTime for timezones

from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.schema import Table, Column, Index, ForeignKey, UniqueConstraint

from . import utils as ut

logger = logging.getLogger(__name__)

##
## Base classes and infra
##

# This is from one of the standard sqlalchemy recipes:
#     https://github.com/sqlalchemy/sqlalchemy/wiki/UniqueObject
class UniqueMixin(object):
    @staticmethod
    def _unique(session, cls, hashfunc, queryfunc, constructor, args, kwargs):
        cache = getattr(session, '_unique_cache', None)
        if cache is None:
            session._unique_cache = cache = {}

        key = (cls, hashfunc(*args, **kwargs))
        if key in cache:
            return cache[key]
        else:
            with session.no_autoflush:
                q = session.query(cls)
                q = queryfunc(q, *args, **kwargs)
                obj = q.first()
                if not obj:
                    obj = constructor(*args, **kwargs)
                    session.add(obj)
            cache[key] = obj
            return obj

    @classmethod
    def unique_hash(cls, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def unique_filter(cls, query, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def as_unique(cls, session, *args, **kwargs):
        return cls._unique(session, cls, cls.unique_hash, cls.unique_filter,
                           cls, args, kwargs)

# The @declared_attr is a bit of a hack - it puts the columns at the end in
# tables, which declaring them as class attributes doesn't
class TimestampsMixin(object):
    @declared_attr
    def insert_dt(cls):
        return Column(TIMESTAMP(timezone=True), server_default=func.now(),
               nullable=False)

    @declared_attr
    def modified_dt(cls):
        return Column(TIMESTAMP(timezone=True), server_default=func.now(),
                      onupdate=func.now(), nullable=False)

@as_declarative()
class Base(object):
    @declared_attr
    def __tablename__(cls):
        return '_'.join(ut.split_camel_case(cls.__name__)).lower()

    def _repr(self, **fields):
        '''
        Helper for Base.__repr__ or subclasses with their own __repr__
        '''

        field_strings = []
        at_least_one_attached_attribute = False
        for key, field in fields.items():
            try:
                field_strings.append(f'{key}={field!r}')
            except sa.orm.exc.DetachedInstanceError:
                field_strings.append(f'{key}=DetachedInstanceError')
            else:
                at_least_one_attached_attribute = True
        if at_least_one_attached_attribute:
            return f"<{self.__class__.__name__}({','.join(field_strings)})>"
        return f"<{self.__class__.__name__} {id(self)}>"

    def __repr__(self):
        fieldnames = sa.inspect(self.__class__).columns.keys()
        fields = {n : getattr(self, n) for n in fieldnames}

        return self._repr(**fields)

# Store the creating package version in the DB to enable migrations
class SchemaVersion(TimestampsMixin, Base):
    version = Column(String(64), primary_key=True, nullable=False)

##
## Users, user tags and Twitter lists
##

class User(TimestampsMixin, Base):
    # this is the Twitter user id, not a surrogate key.
    # it simplifies the load process to use it as a pk.
    user_id = Column(BigInteger, primary_key=True, autoincrement=False)

    data = relationship('UserData', back_populates='user')
    lists_owned = relationship('List', back_populates='owning_user')
    list_memberships = relationship('UserList', back_populates='user')
    tags = relationship('Tag', secondary=lambda: UserTag.__table__,
                        back_populates='users')
    tweets = relationship('Tweet', back_populates='user')
    mentions = relationship('UserMention', back_populates='user')

    @classmethod
    def from_tweepy(cls, obj, session=None):
        return cls(user_id=obj.id)

class UserData(TimestampsMixin, Base):
    user_data_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                     nullable=False)
    url_id = Column(BigInteger, ForeignKey('url.url_id', deferrable=True),
                    nullable=True)

    api_response = Column(UnicodeText, nullable=False)

    screen_name = Column(String(256), nullable=True)
    create_dt = Column(TIMESTAMP(timezone=True), nullable=True)
    protected = Column(Boolean, nullable=True)
    verified = Column(Boolean, nullable=True)
    display_name = Column(UnicodeText, nullable=True)
    description = Column(UnicodeText, nullable=True)
    location = Column(UnicodeText, nullable=True)
    friends_count = Column(BigInteger, nullable=True)
    followers_count = Column(BigInteger, nullable=True)
    listed_count = Column(Integer, nullable=True)

    user = relationship('User', back_populates='data')
    url = relationship('Url', back_populates='user_data')

    @classmethod
    def from_tweepy(cls, obj, session=None):
        # Twitter sometimes includes NUL bytes, which might be handled correctly
        # by sqlalchemy + backend or might not: handling them is risky. We'll
        # just drop them to be safe.
        api_response = json.dumps(obj._json) # NOTE not public API
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'user_id': obj.id,
            'screen_name': obj.screen_name,
            'create_dt': obj.created_at,
            'api_response': api_response
        }

        extra_fields = {
            'protected': 'protected',
            'verified': 'verified',
            'display_name': 'name',
            'description': 'description',
            'location': 'location',
            'friends_count': 'friends_count',
            'followers_count': 'followers_count',
            'listed_count': 'listed_count'
        }

        for t, s in extra_fields.items():
            if hasattr(obj, s):
                args[t] = getattr(obj, s)

        ret = cls(**args)

        ## Populate the url field
        url = None

        try:
            url = obj.entities['url']['urls'][0]['expanded_url']
        except Exception:
            pass

        try:
            if url is None:
                url = obj.entities['url']['urls'][0]['display_url']
        except Exception:
            pass

        try:
            if url is None:
                url = obj.entities['url']['urls'][0]['url']
        except Exception:
            pass

        try:
            if url is None:
                url = obj.url
        except Exception:
            pass

        if url is not None:
            ret.url = Url.as_unique(session, url=url)

        return ret

class Tag(TimestampsMixin, Base):
    tag_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(UnicodeText, nullable=False, unique=True)

    users = relationship('User', secondary=lambda: UserTag.__table__,
                         back_populates='tags')

class List(TimestampsMixin, Base):
    # as in Tweet and User, list_id is Twitter's id rather than a surrogate key
    list_id = Column(BigInteger, primary_key=True, autoincrement=False)
    user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                     nullable=False)

    slug = Column(UnicodeText, nullable=False)
    api_response = Column(UnicodeText, nullable=False)

    create_dt = Column(TIMESTAMP(timezone=True), nullable=True)
    full_name = Column(UnicodeText, nullable=True)
    display_name = Column(UnicodeText, nullable=True)
    uri = Column(UnicodeText, nullable=True)
    description = Column(UnicodeText, nullable=True)
    mode = Column(UnicodeText, nullable=True)
    member_count = Column(Integer, nullable=True)
    subscriber_count = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'slug', deferrable=True),
    )

    owning_user = relationship('User', back_populates='lists_owned')
    list_memberships = relationship('UserList', back_populates='lst')

    @classmethod
    def from_tweepy(cls, obj, session=None):
        # remove NUL bytes as above
        api_response = json.dumps(obj._json)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'list_id': obj.id,
            'user_id': obj.user.id,
            'slug': obj.slug,
            'api_response': api_response
        }

        extra_fields = {
            'create_dt': 'created_at',
            'display_name': 'name',
            'uri': 'uri',
            'description': 'description',
            'mode': 'mode',
            'member_count': 'member_count',
            'subscriber_count': 'subscriber_count'
        }

        for t, s in extra_fields.items():
            if hasattr(obj, s):
                args[t] = getattr(obj, s)

        # other fields that take special handling
        if hasattr(obj, 'full_name'):
            args['full_name'] = obj.full_name[1:]

        return cls(**args)

class UserList(Base):
    user_list_id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                     nullable=False)
    list_id = Column(BigInteger, ForeignKey('list.list_id', deferrable=True),
                     nullable=False)

    valid_start_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                            nullable=False)
    valid_end_dt = Column(TIMESTAMP(timezone=True), nullable=True)

    lst = relationship('List', back_populates='list_memberships')
    user = relationship('User', back_populates='list_memberships')

class UserTag(TimestampsMixin, Base):
    user_tag_id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                     nullable=False)
    tag_id = Column(Integer, ForeignKey('tag.tag_id', deferrable=True),
                    nullable=False)

    __table_args__ = (UniqueConstraint('user_id', 'tag_id'),)

##
## Follow graph
##

class Follow(Base):
    follow_id = Column(BigInteger, primary_key=True, autoincrement=True)

    source_user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                            nullable=False)
    target_user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                            nullable=False)

    valid_start_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                            nullable=False)
    valid_end_dt = Column(TIMESTAMP(timezone=True), nullable=True)

# A temp-ish table for SCD operations on Follow
class StgFollow(Base):
    source_user_id = Column(BigInteger, primary_key=True, autoincrement=False)
    target_user_id = Column(BigInteger, primary_key=True, autoincrement=False)

##
## Tweets and tweet entities
##

class Tweet(TimestampsMixin, Base):
    # as in User, this is the Twitter id rather than a surrogate key
    tweet_id = Column(BigInteger, primary_key=True, autoincrement=False)
    user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                     nullable=False)

    retweeted_status_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                                 nullable=True)
    quoted_status_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                              nullable=True)

    api_response = Column(UnicodeText, nullable=False)
    content = Column(UnicodeText, nullable=False)
    create_dt = Column(TIMESTAMP(timezone=True), nullable=False)

    # we don't get this back on the Twitter API response, can't assume the
    # corresponding tweet row is present in this table
    in_reply_to_status_id = Column(BigInteger, nullable=True)
    in_reply_to_user_id = Column(BigInteger, nullable=True)

    lang = Column(String(8), nullable=True)
    source = Column(UnicodeText, nullable=True)
    truncated = Column(Boolean, nullable=True)
    retweet_count = Column(Integer, nullable=True)
    favorite_count = Column(Integer, nullable=True)

    user = relationship('User', foreign_keys=[user_id], back_populates='tweets')

    retweet_of = relationship('Tweet', foreign_keys=[retweeted_status_id],
                              remote_side=[tweet_id])
    quote_of = relationship('Tweet', foreign_keys=[quoted_status_id],
                            remote_side=[tweet_id])

    user_mentions = relationship('UserMention', back_populates='tweet')
    hashtag_mentions = relationship('HashtagMention', back_populates='tweet')
    symbol_mentions = relationship('SymbolMention', back_populates='tweet')
    url_mentions = relationship('UrlMention', back_populates='tweet')

    @classmethod
    def from_tweepy(cls, obj, session=None):
        # remove NUL bytes as above
        api_response = json.dumps(obj._json)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'tweet_id': obj.id,
            'user_id': obj.user.id,
            'create_dt': obj.created_at,
            'api_response': api_response
        }

        if hasattr(obj, 'full_text'):
            args['content'] = obj.full_text
        else:
            args['content'] = obj.text

        extra_fields = [
            'in_reply_to_status_id',
            'in_reply_to_user_id',

            'lang',
            'source',
            'truncated',
            'retweet_count',
            'favorite_count'
        ]

        for t in extra_fields:
            if hasattr(obj, t):
                val = getattr(obj, t)
                args[t] = (val if val != 'null' else None)

        ret = cls(**args)

        ret.user = User.from_tweepy(obj.user, session)

        # NOTE We've decided not to use this data. There's too much
        # of it and it doesn't add enough value for the amount of space
        # it takes up (relative to just the explicit fetches via UserInfoJob).
        # Implementing SCD on this table would also be too much work, and
        # given that the followers/friends/listed counts change rapidly, would
        # still take up too much space.
        # ret.user.data.append(UserData.from_tweepy(obj.user, session))

        if hasattr(obj, 'quoted_status'):
            ret.quote_of = Tweet.from_tweepy(obj.quoted_status, session)

        if hasattr(obj, 'retweeted_status'):
            ret.retweet_of = Tweet.from_tweepy(obj.retweeted_status, session)

        ret.user_mentions = UserMention.list_from_tweepy(obj, session)
        ret.hashtag_mentions = HashtagMention.list_from_tweepy(obj, session)
        ret.symbol_mentions = SymbolMention.list_from_tweepy(obj, session)
        ret.url_mentions = UrlMention.list_from_tweepy(obj, session)

        return ret

class Hashtag(TimestampsMixin, UniqueMixin, Base):
    hashtag_id = Column(BigInteger, primary_key=True, autoincrement=True)

    name = Column(UnicodeText, nullable=False, index=True, unique=True)

    mentions = relationship('HashtagMention', back_populates='hashtag',
                            cascade_backrefs=False)

    @classmethod
    def unique_hash(cls, name):
        return name

    @classmethod
    def unique_filter(cls, query, name):
        return query.filter(cls.name == name)

class Symbol(TimestampsMixin, UniqueMixin, Base):
    symbol_id = Column(BigInteger, primary_key=True, autoincrement=True)

    name = Column(UnicodeText, nullable=False, index=True, unique=True)

    mentions = relationship('SymbolMention', back_populates='symbol',
                            cascade_backrefs=False)

    @classmethod
    def unique_hash(cls, name):
        return name

    @classmethod
    def unique_filter(cls, query, name):
        return query.filter(cls.name == name)

class Url(TimestampsMixin, UniqueMixin, Base):
    url_id = Column(BigInteger, primary_key=True, autoincrement=True)

    url = Column(UnicodeText, nullable=False, index=True, unique=True)

    mentions = relationship('UrlMention', back_populates='url',
                            cascade_backrefs=False)
    user_data = relationship('UserData', back_populates='url',
                             cascade_backrefs=False)

    @classmethod
    def unique_hash(cls, url):
        return url

    @classmethod
    def unique_filter(cls, query, url):
        return query.filter(cls.url == url)

class UserMention(TimestampsMixin, Base):
    user_mention_id = Column(BigInteger, primary_key=True, autoincrement=True)

    tweet_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                      nullable=False)
    mentioned_user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                               nullable=False)

    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)

    tweet = relationship('Tweet', back_populates='user_mentions')
    user = relationship('User', back_populates='mentions')

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'user_mentions' in obj.entities.keys():
                for mt in obj.entities['user_mentions']:
                    kwargs = {
                        'tweet_id': obj.id,
                        'mentioned_user_id': mt['id'],
                        'start_index': mt['indices'][0],
                        'end_index': mt['indices'][1]
                    }

                    ret = cls(**kwargs)
                    ret.user = User.from_tweepy(obj.user, session)

                    lst += [ret]

        return lst

class HashtagMention(TimestampsMixin, Base):
    hashtag_mention_id = Column(BigInteger, primary_key=True, autoincrement=True)

    tweet_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                      nullable=False)
    hashtag_id = Column(BigInteger, ForeignKey('hashtag.hashtag_id', deferrable=True),
                        nullable=False)

    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)

    tweet = relationship('Tweet', back_populates='hashtag_mentions')
    hashtag = relationship('Hashtag', back_populates='mentions')

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'hashtags' in obj.entities.keys():
                for mt in obj.entities['hashtags']:
                    kwargs = {
                        'tweet_id': obj.id,
                        'start_index': mt['indices'][0],
                        'end_index': mt['indices'][1]
                    }

                    ret = cls(**kwargs)
                    ret.hashtag = Hashtag.as_unique(session, name=mt['text'])

                    lst += [ret]

        return lst

class SymbolMention(TimestampsMixin, Base):
    symbol_mention_id = Column(BigInteger, primary_key=True, autoincrement=True)

    tweet_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                      nullable=False)
    symbol_id = Column(BigInteger, ForeignKey('symbol.symbol_id', deferrable=True),
                       nullable=False)

    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)

    tweet = relationship('Tweet', back_populates='symbol_mentions')
    symbol = relationship('Symbol', back_populates='mentions')

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'symbols' in obj.entities.keys():
                for mt in obj.entities['symbols']:
                    kwargs = {
                        'tweet_id': obj.id,
                        'start_index': mt['indices'][0],
                        'end_index': mt['indices'][1]
                    }

                    ret = cls(**kwargs)
                    ret.symbol = Symbol.as_unique(session, name=mt['text'])

                    lst += [ret]

        return lst

class UrlMention(TimestampsMixin, Base):
    url_mention_id = Column(BigInteger, primary_key=True, autoincrement=True)

    tweet_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                      nullable=False)
    url_id = Column(BigInteger, ForeignKey('url.url_id', deferrable=True),
                    nullable=False)

    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)

    # These are properties of the specific URL mention, not the page at the
    # other end
    twitter_short_url = Column(UnicodeText, nullable=True)
    expanded_short_url = Column(UnicodeText, nullable=True)

    # It's less obvious, but these are also properties of the URL mention, not
    # the URL itself, because they have a time dimension. (The page behind the
    # URL can change over time.)
    status = Column(Integer, nullable=True)
    title = Column(UnicodeText, nullable=True)
    description = Column(UnicodeText, nullable=True)

    tweet = relationship('Tweet', back_populates='url_mentions')
    url = relationship('Url', back_populates='mentions')

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'urls' in obj.entities.keys():
                for mt in obj.entities['urls']:
                    kwargs = {
                        'tweet_id': obj.id,

                        'twitter_short_url': mt['url'],
                        'start_index': mt['indices'][0],
                        'end_index': mt['indices'][1]
                    }

                    if 'unwound' in mt.keys():
                        kwargs['status'] = mt['unwound']['status']
                        kwargs['title'] = mt['unwound']['title']
                        kwargs['description'] = mt['unwound']['description']

                        kwargs['expanded_short_url'] = mt['expanded_url']
                        url = mt['unwound']['url']
                    else:
                        kwargs['expanded_short_url'] = None
                        url = mt['expanded_url']

                    ret = cls(**kwargs)
                    ret.url = Url.as_unique(session, url=url)

                    lst += [ret]

        return lst

