# FIXME indexes from existing sql script
# FIXME factor out SCD for user data?

import json
import logging
import datetime as dt

from abc import ABC, abstractmethod

import sqlalchemy.sql.functions as func

from sqlalchemy.schema import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.types import INT, BIGINT, VARCHAR, TEXT, TIMESTAMP, BOOLEAN
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

class TweepyMixin(object):
    @classmethod
    @abstractmethod
    def from_tweepy(cls, obj):
        raise NotImplementedError()

Base = declarative_base()

##
## Primary objects
##

class User(Base, TweepyMixin):
    __tablename__ = 'user'

    # this is the Twitter user id, not a surrogate key.
    # it simplifies the load process to use it as a pk.
    user_id = Column(BIGINT, primary_key=True, autoincrement=False)

    # api_response is nullable because not every user recorded
    # here was obtained from its own API call: some are mentioned
    # in tweets or returned as followers / friends
    api_response = Column(TEXT, nullable=True)
    screen_name = Column(VARCHAR(256), nullable=True)
    account_create_dt = Column(TIMESTAMP(timezone=True), nullable=True)
    protected = Column(BOOLEAN, nullable=True)
    verified = Column(BOOLEAN, nullable=True)
    name = Column(TEXT, nullable=True)
    description = Column(TEXT, nullable=True)
    location = Column(TEXT, nullable=True)
    url = Column(TEXT, nullable=True)

    insert_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       nullable=False)
    modified_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    lists_owned = relationship('List', back_populates='owning_user')
    tags = relationship('Tag', secondary='user_tag', back_populates='users')
    tweets = relationship('Tweet', back_populates='user')
    mentions = relationship('Tweet', secondary='mention',
                            back_populates='mentioned')

    @classmethod
    def from_tweepy(cls, obj):
        # Twitter sometimes includes NUL bytes, which might be handled correctly
        # by sqlalchemy + backend or might not: handling them is risky. We'll
        # just drop them to be safe.
        api_response = json.dumps(obj._json)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'user_id': obj.id,
            'screen_name': obj.screen_name,
            'api_response': api_response, # NOTE is this public API?
            'account_create_dt': obj.created_at.replace(tzinfo=dt.timezone.utc)
        }

        extra_fields = {
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

class List(Base, TweepyMixin):
    __tablename__ = 'list'

    list_id = Column(BIGINT, primary_key=True, autoincrement=False)
    user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True),
                     nullable=False)

    api_response = Column(TEXT, nullable=False)
    slug = Column(TEXT, nullable=False)

    list_create_dt = Column(TIMESTAMP(timezone=True), nullable=True)
    name = Column(TEXT, nullable=True)
    full_name = Column(TEXT, nullable=True)
    uri = Column(TEXT, nullable=True)
    description = Column(TEXT, nullable=True)
    mode = Column(TEXT, nullable=True)
    member_count = Column(INT, nullable=True)
    subscriber_count = Column(INT, nullable=True)

    insert_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       nullable=False)
    modified_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    owning_user = relationship('User', back_populates='lists_owned')

    @classmethod
    def from_tweepy(cls, obj):
        # Twitter sometimes includes NUL bytes, which might be handled correctly
        # by sqlalchemy + backend or might not: handling them is risky. We'll
        # just drop them to be safe.
        api_response = json.dumps(obj._json)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'list_id': obj.id,
            'user_id': obj.user.id,
            'slug': obj.slug,
            'api_response': api_response, # NOTE is this public API?
        }

        extra_fields = {
            'list_create_dt': 'created_at',
            'name': 'name',
            'full_name': 'full_name',
            'uri': 'uri',
            'description': 'description',
            'mode': 'mode',
            'member_count': 'member_count',
            'subscriber_count': 'subscriber_count'
        }

        for t, s in extra_fields.items():
            if hasattr(obj, s):
                args[t] = getattr(obj, s)

        return cls(**args)

class UserList(Base):
    __tablename__ = 'user_list'

    user_list_id = Column(BIGINT, primary_key=True, autoincrement=True)

    user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True))
    list_id = Column('list_id', BIGINT, ForeignKey('list.list_id', deferrable=True))

    valid_start_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                            nullable=False)
    valid_end_dt = Column(TIMESTAMP(timezone=True), nullable=True)

class Tweet(Base, TweepyMixin):
    __tablename__ = 'tweet'

    # as in User, this is the Twitter id rather than a surrogate key
    tweet_id = Column(BIGINT, primary_key=True, autoincrement=False)
    user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True),
                     nullable=False)

    api_response = Column(TEXT, nullable=False)
    content = Column(TEXT, nullable=False)
    tweet_create_dt = Column(TIMESTAMP(timezone=True), nullable=False)

    lang = Column(VARCHAR(8), nullable=True)
    source = Column(TEXT, nullable=True)
    truncated = Column(BOOLEAN, nullable=True)
    retweet_count = Column(INT, nullable=True)
    favorite_count = Column(INT, nullable=True)

    # the IDs here aren't FKs because we haven't
    # necessarily fetched the corresponding tweets
    retweeted_status_id = Column(BIGINT, nullable=True)
    in_reply_to_user_id = Column(BIGINT, nullable=True)
    quoted_status_id = Column(BIGINT, nullable=True)
    quoted_status_content = Column(TEXT, nullable=True)

    insert_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       nullable=False)
    modified_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    tags = relationship('Tag', secondary='tweet_tag', back_populates='tweets')
    user = relationship('User', back_populates='tweets')
    mentioned = relationship('User', secondary='mention',
                             back_populates='mentions')

    @classmethod
    def from_tweepy(cls, obj):
        # remove NUL bytes as above
        api_response = json.dumps(obj._json)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'tweet_id': obj.id,
            'user_id': obj.user.id,
            'api_response': api_response, # NOTE is this public API?
            'tweet_create_dt': obj.created_at.replace(tzinfo=dt.timezone.utc)
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
            'quoted_status_id',
            # 'quoted_status_content',
            'in_reply_to_user_id',
            'in_reply_to_status_id',
            'retweet_count',
            'favorite_count'
        ]

        for t in extra_fields:
            if hasattr(obj, t):
                val = getattr(obj, t)
                val = (val if val != 'null' else None)

                args[t] = val

        if hasattr(obj, 'quoted_status'):
            if hasattr(obj.quoted_status, 'full_text'):
                args['quoted_status_content'] = obj.quoted_status.full_text
            else:
                args['quoted_status_content'] = obj.quoted_status.text

        # Native retweets take some special handling
        if hasattr(obj, 'retweeted_status'):
            args['retweeted_status_id'] = obj.retweeted_status.id

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

class Tag(Base):
    __tablename__ = 'tag'

    tag_id = Column(BIGINT, primary_key=True, autoincrement=True)
    name = Column(TEXT, nullable=False)

    users = relationship('User', secondary='user_tag', back_populates='tags')
    tweets = relationship('Tweet', secondary='tweet_tag', back_populates='tags')

class Follow(Base):
    __tablename__ = 'follow'

    follow_id = Column(BIGINT, primary_key=True, autoincrement=True)

    source_user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True),
                            nullable=False)
    target_user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True),
                            nullable=False)

    valid_start_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                            nullable=False)
    valid_end_dt = Column(TIMESTAMP(timezone=True), nullable=True)

    # FIXME are these reversed?
    followers = relationship('User', foreign_keys=[source_user_id],
                             backref='followers')
    friends = relationship('User', foreign_keys=[target_user_id],
                           backref='friends')

##
## Link tables, whether or not considered as objects
##

user_tag = Table('user_tag', Base.metadata,
    Column('user_id', BIGINT, ForeignKey('user.user_id', deferrable=True),
           primary_key=True),
    Column('tag_id', BIGINT, ForeignKey('tag.tag_id', deferrable=True),
           primary_key=True)
)

tweet_tag = Table('tweet_tag', Base.metadata,
    Column('tweet_id', BIGINT, ForeignKey('tweet.tweet_id', deferrable=True),
           primary_key=True),
    Column('tag_id', BIGINT, ForeignKey('tag.tag_id', deferrable=True),
           primary_key=True)
)

mention = Table('mention', Base.metadata,
    Column('tweet_id', BIGINT, ForeignKey('tweet.tweet_id', deferrable=True),
           primary_key=True),
    Column('mentioned_user_id', BIGINT, ForeignKey('user.user_id',
                                                   deferrable=True),
           primary_key=True)
)

class UserTag(Base):
    __table__ = user_tag

class TweetTag(Base):
    __table__ = tweet_tag

class Mention(Base):
    __table__ = mention

##
## Utility functions
##

def mentions_from_tweet(tweet):
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

