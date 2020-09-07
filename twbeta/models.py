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

import twbeta.utils as ut

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
    tags = relationship('Tag', secondary=lambda: UserTag.__table__,
                        back_populates='users')
    tweets = relationship('Tweet', back_populates='user')
    mentions = relationship('Tweet', secondary=lambda: Mention.__table__,
                            back_populates='mentioned')

    @classmethod
    def from_tweepy(cls, obj):
        return cls(user_id=obj.id)

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
        api_response = json.dumps(obj._json) # NOTE not public API
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        args = {
            'user_id': obj.id,
            'screen_name': obj.screen_name,
            'account_create_dt': obj.created_at,
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

        ## Fallback logic for the url field
        try:
            args['url'] = obj.entities['url']['urls'][0]['expanded_url']
        except Exception:
            pass

        try:
            if 'url' not in args.keys():
                args['url'] = obj.entities['url']['urls'][0]['display_url']
        except Exception:
            pass

        try:
            if 'url' not in args.keys():
                args['url'] = obj.entities['url']['urls'][0]['url']
        except Exception:
            pass

        try:
            if 'url' not in args.keys():
                args['url'] = obj.url
        except Exception:
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
            'list_create_dt': 'created_at',
            'name': 'name',
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
    in_reply_to_status_id = Column(BIGINT, nullable=True)
    quoted_status_id = Column(BIGINT, nullable=True)
    quoted_status_content = Column(TEXT, nullable=True)

    insert_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       nullable=False)
    modified_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    tags = relationship('Tag', secondary=lambda: TweetTag.__table__,
                        back_populates='tweets')
    user = relationship('User', back_populates='tweets')
    mentioned = relationship('User', secondary=lambda: Mention.__table__,
                             back_populates='mentions')

    @classmethod
    def from_tweepy(cls, obj):
        # remove NUL bytes as above
        api_response = json.dumps(obj._json)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '')

        print(json.dumps(obj._json, indent=4))

        args = {
            'tweet_id': obj.id,
            'user_id': obj.user.id,
            'tweet_create_dt': obj.created_at,
            'api_response': api_response
        }

        if hasattr(obj, 'full_text'):
            args['content'] = obj.full_text
        else:
            args['content'] = obj.text

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
            if hasattr(obj, t):
                val = getattr(obj, t)
                args[t] = (val if val != 'null' else None)

        # other fields needing special handling
        # FIXME should we update user_data with the user info that comes back?
        # FIXME what about loading replies? do those come back with the response?
        # FIXME should we load the quoted status too?
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
            if hasattr(obj, 'full_text'):
                args['content'] = obj.retweeted_status.full_text
            else:
                args['content'] = objretweeted_status.text

        return cls(**args)

    @staticmethod
    def mentioned_users_from_tweepy(obj):
        users = []

        if hasattr(obj, 'entities'):
            if 'user_mentions' in objentities.keys():
                for m in tweet.entities['user_mentions']:
                    users += [m['id']]

        return users

class Tag(Base):
    tag_id = Column(BIGINT, primary_key=True, autoincrement=True)
    name = Column(TEXT, nullable=False, unique=True)

    insert_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       nullable=False)
    modified_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    users = relationship('User', secondary=lambda: UserTag.__table__,
                         back_populates='tags')
    tweets = relationship('Tweet', secondary=lambda: TweetTag.__table__,
                          back_populates='tags')

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

class UserTag(Base):
    user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True),
                     primary_key=True)
    tag_id = Column(BIGINT, ForeignKey('tag.tag_id', deferrable=True),
                    primary_key=True)

    insert_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       nullable=False)
    modified_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

class TweetTag(Base):
    tweet_id = Column(BIGINT, ForeignKey('tweet.tweet_id', deferrable=True),
           primary_key=True)
    tag_id = Column(BIGINT, ForeignKey('tag.tag_id', deferrable=True),
           primary_key=True)

class Mention(Base):
    tweet_id = Column(BIGINT, ForeignKey('tweet.tweet_id', deferrable=True),
           primary_key=True)
    mentioned_user_id = Column(BIGINT, ForeignKey('user.user_id', deferrable=True),
           primary_key=True)

    insert_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       nullable=False)
    modified_dt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

