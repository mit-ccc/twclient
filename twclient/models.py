import json
import hashlib
import logging

from abc import ABC, abstractmethod

import sqlalchemy as sa
import sqlalchemy.sql.functions as func

from sqlalchemy.types import Boolean, Integer, BigInteger, String, UnicodeText
from sqlalchemy.types import TIMESTAMP # recommended over DateTime for timezones
from sqlalchemy.types import Float, Enum

from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.schema import Table, Column, Index, ForeignKey
from sqlalchemy.schema import UniqueConstraint, CheckConstraint

from . import utils as ut

logger = logging.getLogger(__name__)

##
## Base classes and infra
##

# This is from one of the standard sqlalchemy recipes:
#     https://github.com/sqlalchemy/sqlalchemy/wiki/UniqueObject
class UniqueMixin(object):
    @staticmethod
    def _unique(session, cls, hashfunc, queryfunc, constructor, kwargs):
        cache = getattr(session, '_unique_cache', None)
        if cache is None:
            session._unique_cache = cache = {}

        key = (cls, hashfunc(**kwargs))
        if key in cache:
            return cache[key]
        else:
            with session.no_autoflush:
                q = session.query(cls)
                q = queryfunc(q, **kwargs)
                obj = q.first()
                if not obj:
                    obj = constructor(**kwargs)
                    session.add(obj)
            cache[key] = obj
            return obj

    @classmethod
    def unique_hash(cls, **kwargs):
        keys = sorted(kwargs.keys())
        s = ', '.join([str(k) + ': ' + str(kwargs[k]) for k in keys])
        s = s.encode('utf-8')

        return hashlib.sha1(s).hexdigest()

    @classmethod
    def unique_filter(cls, query, url):
        return query.filter(cls.url == url)

    @classmethod
    def unique_filter(cls, query, **kwargs):
        flts = [
            getattr(cls, key) == kwargs[key]
            for key in kwargs.keys()
        ]

        return query.filter(*flts)

    @classmethod
    def as_unique(cls, session, **kwargs):
        return cls._unique(session, cls, cls.unique_hash, cls.unique_filter,
                           cls, kwargs)

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

# Store the creating package version in the DB to enable migrations (we don't
# actually do any migrations or have any code to support them yet, but if this
# isn't here to begin with it'll be a gigantic pain)
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
                     nullable=False, index=True)
    url_id = Column(BigInteger, ForeignKey('url.url_id', deferrable=True),
                    nullable=True, index=True)

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
                     nullable=False) # no index needed given unique below

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

    __table_args__ = (UniqueConstraint('user_id', 'slug'),)

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
                     nullable=False) # no index needed given unique below
    list_id = Column(BigInteger, ForeignKey('list.list_id', deferrable=True),
                     nullable=False, index=True)

    valid_start_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                            nullable=False)
    valid_end_dt = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'list_id', 'valid_end_dt',
                         'valid_start_dt'),
    )

    lst = relationship('List', back_populates='list_memberships')
    user = relationship('User', back_populates='list_memberships')

class UserTag(TimestampsMixin, Base):
    user_tag_id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                     nullable=False) # no index needed given unique below
    tag_id = Column(Integer, ForeignKey('tag.tag_id', deferrable=True),
                    nullable=False, index=True)

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

    __table_args__ = (
        # NOTE more testing needed to ensure these indexes work as intended

        # The unique index generated here participates in the INSERT and the
        # subquery of the UPDATE that load new StgFollow data. When writing the
        # sort of query that can use it (e.g., get a user's current followers),
        # it has the extra benefit of being a covering index.
        UniqueConstraint('source_user_id', 'target_user_id', 'valid_end_dt',
                         'valid_start_dt'),

        # These are intended to help answer the UPDATE statements issued in
        # processing new data loaded to StgFollow.
        Index('idx_follow_source_user_id_valid_end_dt', 'source_user_id',
              'valid_end_dt'),
        Index('idx_follow_target_user_id_valid_end_dt', 'target_user_id',
              'valid_end_dt')
    )


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
                     nullable=False, index=True)

    retweeted_status_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                                 nullable=True, index=True)
    quoted_status_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                              nullable=True, index=True)

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
    media_mentions = relationship('MediaMention', back_populates='tweet')

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
        ret.media_mentions = MediaMention.list_from_tweepy(obj, session)

        return ret

class Hashtag(TimestampsMixin, UniqueMixin, Base):
    hashtag_id = Column(BigInteger, primary_key=True, autoincrement=True)

    name = Column(UnicodeText, nullable=False, unique=True)

    mentions = relationship('HashtagMention', back_populates='hashtag',
                            cascade_backrefs=False)

class Symbol(TimestampsMixin, UniqueMixin, Base):
    symbol_id = Column(BigInteger, primary_key=True, autoincrement=True)

    name = Column(UnicodeText, nullable=False, unique=True)

    mentions = relationship('SymbolMention', back_populates='symbol',
                            cascade_backrefs=False)

class Url(TimestampsMixin, UniqueMixin, Base):
    url_id = Column(BigInteger, primary_key=True, autoincrement=True)

    url = Column(UnicodeText, nullable=False, unique=True)

    mentions = relationship('UrlMention', back_populates='url',
                            cascade_backrefs=False)
    user_data = relationship('UserData', back_populates='url',
                             cascade_backrefs=False)
    media = relationship('Media', back_populates='url',
                         cascade_backrefs=False)
    media_variants = relationship('MediaVariant', back_populates='url',
                                  cascade_backrefs=False)

class MediaType(TimestampsMixin, UniqueMixin, Base):
    media_type_id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(UnicodeText, nullable=False, unique=True)

    media = relationship('Media', back_populates='media_type',
                         cascade_backrefs=False)

class Media(TimestampsMixin, Base):
    # Twitter gives these IDs, so unlike with the other entities we don't have
    # to make one up
    media_id = Column(BigInteger, primary_key=True, autoincrement=False)

    media_type_id = Column(Integer, ForeignKey('media_type.media_type_id', deferrable=True),
                           nullable=False)
    media_url_id = Column(BigInteger, ForeignKey('url.url_id', deferrable=True),
                          nullable=False)

    # video-specific attributes
    aspect_ratio_width = Column(Integer, nullable=True)
    aspect_ratio_height = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)

    media_type = relationship('MediaType', back_populates='media')
    url = relationship('Url', back_populates='media')
    variants = relationship('MediaVariant', back_populates='media')
    mentions = relationship('MediaMention', back_populates='media',
                            cascade_backrefs=False)

class MediaVariant(TimestampsMixin, Base):
    media_id = Column(BigInteger, ForeignKey('media.media_id', deferrable=True),
                      primary_key=True, autoincrement=False)
    url_id = Column(BigInteger, ForeignKey('url.url_id', deferrable=True),
                    primary_key=True, autoincrement=False)

    bitrate = Column(Integer, nullable=True)
    content_type = Column(UnicodeText, nullable=True)

    url = relationship('Url', back_populates='media_variants')
    media = relationship('Media', back_populates='variants',
                         cascade_backrefs=False)

class UserMention(TimestampsMixin, Base):
    tweet_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)
    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    mentioned_user_id = Column(BigInteger, ForeignKey('user.user_id', deferrable=True),
                               nullable=False, index=True)

    user = relationship('User', back_populates='mentions')
    tweet = relationship('Tweet', back_populates='user_mentions')

    __table_args__ = (UniqueConstraint('tweet_id', 'start_index', 'end_index'),)

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'user_mentions' in obj.entities.keys():
                for mt in obj.entities['user_mentions']:
                    kwargs = {
                        'tweet_id': obj.id,
                        'start_index': mt['indices'][0],
                        'end_index': mt['indices'][1]
                    }

                    ret = cls(**kwargs)
                    ret.user = User.from_tweepy(obj.user, session)

                    lst += [ret]

        return lst

class HashtagMention(TimestampsMixin, Base):
    tweet_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)
    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    hashtag_id = Column(BigInteger, ForeignKey('hashtag.hashtag_id', deferrable=True),
                        nullable=False, index=True)

    hashtag = relationship('Hashtag', back_populates='mentions')
    tweet = relationship('Tweet', back_populates='hashtag_mentions',
                         cascade_backrefs=False)

    __table_args__ = (UniqueConstraint('tweet_id', 'start_index', 'end_index'),)

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
    tweet_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)
    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    symbol_id = Column(BigInteger, ForeignKey('symbol.symbol_id', deferrable=True),
                       nullable=False, index=True)

    symbol = relationship('Symbol', back_populates='mentions')
    tweet = relationship('Tweet', back_populates='symbol_mentions',
                         cascade_backrefs=False)

    __table_args__ = (UniqueConstraint('tweet_id', 'start_index', 'end_index'),)

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
    tweet_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)
    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    url_id = Column(BigInteger, ForeignKey('url.url_id', deferrable=True),
                    nullable=False, index=True)

    # These are properties of the specific URL mention, not the page at the
    # other end
    twitter_short_url = Column(UnicodeText, nullable=True)
    twitter_display_url = Column(UnicodeText, nullable=True)
    expanded_short_url = Column(UnicodeText, nullable=True)

    # It's less obvious, but these are also properties of the URL mention, not
    # the URL itself, because they have a time dimension. (The page behind the
    # URL can change over time.)
    status = Column(Integer, nullable=True)
    title = Column(UnicodeText, nullable=True)
    description = Column(UnicodeText, nullable=True)

    url = relationship('Url', back_populates='mentions')
    tweet = relationship('Tweet', back_populates='url_mentions',
                         cascade_backrefs=False)

    __table_args__ = (UniqueConstraint('tweet_id', 'start_index', 'end_index'),)

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'urls' in obj.entities.keys():
                for mt in obj.entities['urls']:
                    kwargs = {
                        'tweet_id': obj.id,
                        'start_index': mt['indices'][0],
                        'end_index': mt['indices'][1]
                    }

                    if 'url' in mt.keys():
                        kwargs['twitter_short_url'] = mt['url']

                    if 'display_url' in mt.keys():
                        kwargs['twitter_display_url'] = mt['display_url']

                    if 'unwound' in mt.keys():
                        kwargs['status'] = mt['unwound']['status']
                        kwargs['title'] = mt['unwound']['title']
                        kwargs['description'] = mt['unwound']['description']

                        kwargs['expanded_short_url'] = mt['expanded_url']
                        url = mt['unwound']['url']
                    else:
                        url = mt['expanded_url']

                    ret = cls(**kwargs)
                    ret.url = Url.as_unique(session, url=url)

                    lst += [ret]

        return lst

class MediaMention(TimestampsMixin, Base):
    tweet_id = Column(BigInteger, ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)
    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    media_id = Column(BigInteger, ForeignKey('media.media_id', deferrable=True),
                      nullable=False, index=True)

    # (Probably) properties of the specific media mention, not the media itself
    twitter_short_url = Column(UnicodeText, nullable=True)
    twitter_display_url = Column(UnicodeText, nullable=True)
    twitter_expanded_url = Column(UnicodeText, nullable=True)

    media = relationship('Media', back_populates='mentions')
    tweet = relationship('Tweet', back_populates='media_mentions',
                         cascade_backrefs=False)

    __table_args__ = (UniqueConstraint('tweet_id', 'start_index', 'end_index'),)

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        # the usual entities object provides incorrect information for media
        # entities: https://developer.twitter.com/en/docs/twitter-api/v1/data-dictionary/overview/extended-entities-object
        if hasattr(obj, 'extended_entities'):
            if 'media' in obj.entities.keys():
                for mt in obj.extended_entities['media']:
                    ##
                    ## The MediaMention object
                    ##

                    kwargs = {
                        'tweet_id': obj.id,
                        'start_index': mt['indices'][0],
                        'end_index': mt['indices'][1]
                    }

                    if 'url' in mt.keys():
                        kwargs['twitter_short_url'] = mt['url']

                    if 'display_url' in mt.keys():
                        kwargs['twitter_display_url'] = mt['display_url']

                    if 'expanded_url' in mt.keys():
                        kwargs['twitter_expanded_url'] = mt['expanded_url']

                    ret = cls(**kwargs)

                    ##
                    ## The Media object
                    ##

                    kwargs = {
                        'media_id': mt['id']
                    }

                    # Info that's only populated for videos
                    if 'video_info' in mt.keys():
                        if 'duration_millis' in mt['video_info'].keys():
                            kwargs['duration'] = 0.001 * mt['video_info']['duration_millis']

                        if 'aspect_ratio' in mt['video_info'].keys():
                            kwargs['aspect_ratio_width'] = mt['video_info']['aspect_ratio'][0]
                            kwargs['aspect_ratio_height'] = mt['video_info']['aspect_ratio'][1]

                    ret.media = Media(**kwargs)

                    # What kind of media?
                    media_type = mt['type']
                    if 'additional_media_info' in mt.keys():
                        if 'embeddable' in mt['additional_media_info'].keys():
                            if not mt['additional_media_info']['embeddable']:
                                media_type = 'unembeddable_video'
                    ret.media.media_type = MediaType.as_unique(session, name=media_type)

                    # The primary url of the media
                    if 'media_url_https' in mt.keys():
                        media_url = mt['media_url_https']
                    else:
                        media_url = mt['media_url']
                    ret.media.url = Url.as_unique(session, url=media_url)

                    ##
                    ## "Variants" aka video files (multiple encodings per Media)
                    ##
                    if 'video_info' in mt.keys():
                        if 'variants' in mt['video_info'].keys():
                            variants = []
                            for v in mt['video_info']['variants']:
                                kwargs = {
                                    'media_id': mt['id']
                                }

                                if 'bitrate' in v.keys():
                                    kwargs['bitrate'] = v['bitrate']

                                if 'content_type' in v.keys():
                                    kwargs['content_type'] = v['content_type']

                                obj = MediaVariant(**kwargs)

                                obj.media = ret.media
                                obj.url = Url.as_unique(session, url=v['url'])

                                variants += [obj]

                            ret.media.variants = variants

                    lst += [ret]

        return lst

