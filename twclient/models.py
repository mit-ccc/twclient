# FIXME indexes from existing sql script

import json
import logging

from abc import ABC, abstractmethod

import sqlalchemy as sa
import sqlalchemy.sql.functions as func

from sqlalchemy.schema import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.types import INT, BIGINT, VARCHAR, TEXT, TIMESTAMP, BOOLEAN
from sqlalchemy.ext.declarative import as_declarative, declared_attr

import twclient.utils as ut

logger = logging.getLogger(__name__)

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

class _TweepyMixin(object):
    @classmethod
    @abstractmethod
    def from_tweepy(cls, obj):
        raise NotImplementedError()

##
## Primary objects
##

class User(Base):
    # this is the Twitter user id, not a surrogate key.
    # it simplifies the load process to use it as a pk.
    user_id = Column(BIGINT, primary_key=True, autoincrement=False)

    insert_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       nullable=False)
    modified_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    data = relationship('UserData', back_populates='user')
    lists_owned = relationship('List', back_populates='owning_user')
    tags = relationship('Tag', secondary='user_tag', back_populates='users')
    tweets = relationship('Tweet', back_populates='user')
    mentions = relationship('Tweet', secondary='mention',
                            back_populates='mentioned')

    @classmethod
    def from_tweepy(cls, obj):
        return cls(user_id=obj['id'])

class UserData(Base, _TweepyMixin):
    user_data_id = Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True),
                     nullable=False)

    api_response = Column(TEXT, nullable=False)
    screen_name = Column(VARCHAR(256), nullable=True)
    account_create_dt = Column(TIMESTAMP(timezone=True), nullable=True)
    protected = Column(BOOLEAN, nullable=True)
    verified = Column(BOOLEAN, nullable=True)
    display_name = Column(TEXT, nullable=True)
    description = Column(TEXT, nullable=True)
    location = Column(TEXT, nullable=True)
    url = Column(TEXT, nullable=True)
    friends_count = Column(BIGINT, nullable=True)
    followers_count = Column(BIGINT, nullable=True)
    listed_count = Column(BIGINT, nullable=True)

    insert_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       nullable=False)
    modified_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    user = relationship('User', back_populates='data')

    @classmethod
    def from_tweepy(cls, obj):
        # Twitter sometimes includes NUL bytes, which might be handled correctly
        # by sqlalchemy + backend or might not: handling them is risky. We'll
        # just drop them to be safe.
        api_response = json.dumps(obj) #, iterable_as_array=True)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'user_id': obj['id'],
            'screen_name': obj['screen_name'],
            'account_create_dt': obj['created_at'],
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
            if s in obj.keys():
                args[t] = obj[s]

        ## Fallback logic for the url field
        try:
            args['url'] = obj['entities']['url']['urls'][0]['expanded_url']
        except (KeyError, IndexError):
            pass

        try:
            if 'url' not in args.keys():
                args['url'] = obj['entities']['url']['urls'][0]['display_url']
        except (KeyError, IndexError):
            pass

        try:
            if 'url' not in args.keys():
                args['url'] = obj['entities']['url']['urls'][0]['url']
        except (KeyError, IndexError):
            pass

        try:
            if 'url' not in args.keys():
                args['url'] = obj['url']
        except (KeyError, IndexError):
            pass

        return cls(**args)

class List(Base, _TweepyMixin):
    list_id = Column(BIGINT, primary_key=True, autoincrement=False)
    user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True),
                     nullable=False)

    slug = Column(TEXT, nullable=False)
    api_response = Column(TEXT, nullable=False)

    list_create_dt = Column(TIMESTAMP(timezone=True), nullable=True)
    full_name = Column(TEXT, nullable=True)
    name = Column(TEXT, nullable=True)
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
        api_response = json.dumps(obj) #, iterable_as_array=True)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'list_id': obj['id'],
            'user_id': obj['user']['id'],
            'slug': obj['slug'],
            'api_response': api_response
        }

        extra_fields = {
            'list_create_dt': 'created_at',
            'name': 'name',
            'uri': 'uri',
            'description': 'description',
            'mode': 'mode',
            'member_count': 'member_count',
            'subscriber_count': 'subscriber_count'
        }

        for t, s in extra_fields.items():
            if s in obj.keys():
                args[t] = obj[s]

        ## Other fields that take special handling
        if 'full_name' in obj.keys():
            args['full_name'] = obj['full_name'][1:]

        return cls(**args)

class UserList(Base):
    user_list_id = Column(BIGINT, primary_key=True, autoincrement=True)

    user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True))
    list_id = Column('list_id', BIGINT, ForeignKey('list.list_id', deferrable=True))

    valid_start_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                            nullable=False)
    valid_end_dt = Column(TIMESTAMP(timezone=True), nullable=True)

class Tweet(Base, _TweepyMixin):
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

    # NOTE the IDs here aren't FKs because we haven't
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
        api_response = json.dumps(obj) #, iterable_as_array=True)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'tweet_id': obj['id'],
            'user_id': obj['user']['id'],
            'tweet_create_dt': obj['created_at'],
            'api_response': api_response
        }

        if 'full_text' in obj.keys():
            args['content'] = obj['full_text']
        else:
            args['content'] = obj['text']

        extra_fields = [
            'lang',
            'source',
            'truncated',
            'quoted_status_id',
            'in_reply_to_user_id',
            'in_reply_to_status_id',
            'retweet_count',
            'favorite_count'
        ]

        for t in extra_fields:
            if t in obj.keys():
                args[t] = (obj[t] if obj[t] != 'null' else None)

        ## Other fields needing special handling
        if 'quoted_status' in obj.keys():
            if 'full_text' in obj['quoted_status'].keys():
                args['quoted_status_content'] = obj['quoted_status']['full_text']
            else:
                args['quoted_status_content'] = obj['quoted_status']['text']

        # Native retweets take some special handling
        if 'retweeted_status' in obj.keys():
            args['retweeted_status_id'] = obj['retweeted_status']['id']

            # From the Twitter docs: "Note that while native retweets may have
            # their toplevel text property shortened, the original text will be
            # available under the retweeted_status object and the truncated
            # parameter will be set to the value of the original status (in most
            # cases, false)."
            if 'full_text' in obj['retweeted_status'].keys():
                args['content'] = obj['retweeted_status']['full_text']
            else:
                args['content'] = obj['retweeted_status']['text']

        return cls(**args)

class Tag(Base):
    tag_id = Column(BIGINT, primary_key=True, autoincrement=True)
    name = Column(TEXT, nullable=False, unique=True)

    users = relationship('User', secondary='user_tag', back_populates='tags')
    tweets = relationship('Tweet', secondary='tweet_tag', back_populates='tags')

class Follow(Base):
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

    @classmethod # FIXME
    def mentions_from_tweet(cls, obj):
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

