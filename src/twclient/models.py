'''
The database schema for storing Twitter data.
'''

import hashlib
import logging

import sqlalchemy as sa
import sqlalchemy.sql.functions as func

from sqlalchemy.types import Boolean, Integer, BigInteger, String, UnicodeText
from sqlalchemy.types import TIMESTAMP  # recommended over DateTime for TZs
from sqlalchemy.types import Float

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, Index, ForeignKey
from sqlalchemy.schema import UniqueConstraint

from . import _utils as ut

if ut.SA_V14:
    from sqlalchemy.orm import as_declarative, declared_attr
else:
    from sqlalchemy.ext.declarative import as_declarative, declared_attr

logger = logging.getLogger(__name__)

# Better to have these all in one file
# pylint: disable=too-many-lines

# Not applicable: database tables have lots of columns
# pylint: disable=too-many-instance-attributes

# This isn't a great way to handle these warnings, but sqlalchemy is so dynamic
# that most attribute accesses aren't resolved until runtime
# pylint: disable=no-member

#
# Base classes and infra
#

def reinitialize(engine):
    '''
    Rebuild / reinitialize the database, dropping and recreating all tables.

    Parameters
    ----------
    engine : instance of sqlalchemy.engine.Engine
        The engine on which to rebuild the database.

    Returns
    -------
    None
    '''

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@as_declarative()
class Base:
    '''
    The base class for sqlalchemy models.

    This class provides some common functionality for sqlalchemy models in
    twclient, including a common table name format.
    '''

    @declared_attr
    def __tablename__(cls):  # pylint: disable=no-self-argument
        return '_'.join(ut.split_camel_case(cls.__name__)).lower()

    def _repr(self, **fields):
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
        fields = {n: getattr(self, n) for n in fieldnames}

        return self._repr(**fields)

    @classmethod
    def clear_fast(cls, session):
        '''
        Clear the table by dropping and recreating it.

        This is much, much faster than .delete() / DELETE FROM <tbl>, but not
        transactional on many DBs.

        Parameters
        ----------
        session : instance of sqlalchemy.orm.Session
            The session in which to clear the table.

        Returns
        -------
        None
        '''

        cls.__table__.drop(session.get_bind())
        cls.__table__.create(session.get_bind())


# This is from one of the standard sqlalchemy recipes:
#     https://github.com/sqlalchemy/sqlalchemy/wiki/UniqueObject
class UniqueMixin:
    '''
    Provide a merge-like operation by unique constraint instead of primary key.

    This class provides an analogue of Session.merge that works on any
    candidate key (set of jointly unique and not null columns) rather than just
    a primary key. The `as_unique` method either a) returns a persistent
    instance of the model if a row with the given unique key values already
    exists or b) creates a new one and adds it to the session.
    '''

    # NOTE this is a mutable class attribute - all instances share it.
    # Probably this would pose garbage collection issues in a long-lived
    # application, but here we don't care.
    _unique_caches = {}

    # As in TimestampsMixin, hack to put the columns at the end in tables,
    # which declaring them as class attributes doesn't
    @declared_attr
    def unique_hash(cls):  # pylint: disable=no-self-argument
        '''
        A hash to implement a unique constraint without length limits.
        '''

        # SHA-1 hashes in hex message digest format are 40 chars
        return Column(String(length=40), nullable=False, unique=True)

    @staticmethod
    def _make_hash(**kwargs):
        keys = sorted(kwargs.keys())

        txt = ', '.join([str(k) + ': ' + str(kwargs[k]) for k in keys])
        txt = txt.encode('utf-8')

        return hashlib.sha1(txt).hexdigest()

    @classmethod
    def as_unique(cls, session, **kwargs):
        '''
        Return an instance of a model, uniquely with respect to a DB session.

        The `as_unique` method either a) returns a persistent instance of the
        class cls if a row with the column values given in kwargs already
        exists or b) creates a new one, adds it to the session and returns the
        newly pending object. The keyword arguments should specify column names
        and their values, and should uniquely identify a particular row. If a
        unique constraint does not exist on the columns, this function may or
        may not work correctly and will be quite slow.

        Parameters
        ----------
        session : instance of sqlalchemy.orm.session.Session
            A sqlalchemy database session.

        **kwargs
            Keyword arguments which should uniquely identify a database row.

        Returns
        -------
        Instance of UniqueMixin
            Instance of the model implementing this API.
        '''

        cls._unique_caches[session] = cls._unique_caches.get(session, {})
        cache = cls._unique_caches[session]

        uhash = cls._make_hash(**kwargs)
        key = (cls, uhash)

        if key in cache:
            return cache[key]

        with session.no_autoflush:
            obj = session.query(cls).filter_by(unique_hash=uhash).one_or_none()

            if not obj:
                obj = cls(unique_hash=uhash, **kwargs)
                session.add(obj)

        cache[key] = obj
        return obj


# The @declared_attr is a bit of a hack - it puts the columns at the end in
# tables, which declaring them as class attributes doesn't
class TimestampsMixin:
    '''
    Add creation and modification timestamps to a model.

    This mixin adds insert_dt and modified_dt columns, and logic to update
    them, to classes descending from it. Nothing else needs to be done in
    subclasses to add these columns.
    '''

    @declared_attr
    def insert_dt(cls):  # pylint: disable=no-self-argument
        '''
        The load time of the row into the database.
        '''

        return Column(TIMESTAMP(timezone=True), server_default=func.now(),
                      nullable=False)

    @declared_attr
    def modified_dt(cls):  # pylint: disable=no-self-argument
        '''
        The last time the row was modified. Note that this field is updated by
        application logic rather than a trigger.
        '''

        return Column(TIMESTAMP(timezone=True), server_default=func.now(),
                      onupdate=func.now(), nullable=False)


class FromTweepyInterface:
    '''
    A model class capable of instantiating itself from a tweepy object.

    Classes implementing this interface provide a from_tweepy method which
    takes a tweepy object and optionally a sqlalchemy database session, and
    returns the instance of the class represented by the tweepy object.
    '''

    # Subclasses are expected to provide this logic, and the implementation
    # here is an abstract stub that raises NotImplementedError.
    @classmethod
    def from_tweepy(cls, obj, session=None):
        '''
        Instantiate a class instance from a tweepy object.

        This method constructs a class instance from a tweepy object. A
        sqlalchemy database session is optional in general but may be required
        by some subclasses which rely on UniqueMixin.as_unique.

        Parameters
        ----------
        obj : instance of tweepy.Model
            The tweepy object to use as data source.

        session : instance of sqlalchemy.orm.session.Session, or None
            A sqlalchemy database session.

        Returns
        -------
        Instance of FromTweepyInterface
            The constructed class instance.
        '''

        raise NotImplementedError()


class ListFromTweepyInterface:
    '''
    A model class capable of instantiating multiple instances of itself from a
    tweepy object.

    Classes implementing this interface provide a list_from_tweepy method which
    takes a tweepy object and optionally a sqlalchemy database session, and
    returns the list of instances of the class which the tweepy object
    represents.
    '''

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        '''
        Return a list of class instances from a tweepy object.

        This method constructs multiple class instances from a tweepy object. A
        sqlalchemy database session is optional in general but may be required
        by some subclasses which rely on UniqueMixin.as_unique. Subclasses are
        expected to provide this logic, and the implementation here is an
        abstract stub that raises NotImplementedError.

        Parameters
        ----------
        obj : instance of tweepy.Model
            The tweepy object to use as data source.

        session : instance of sqlalchemy.orm.session.Session, or None
            A sqlalchemy database session.

        Returns
        -------
        List of instances of FromTweepyInterface
            The constructed class instances.
        '''

        raise NotImplementedError()


# Store the creating package version in the DB to enable migrations (we don't
# actually do any migrations or have any code to support them yet, but if this
# isn't here to begin with it'll be a gigantic pain)
@ut.export
class SchemaVersion(TimestampsMixin, Base):
    '''
    A stub table to store the schema version.

    This table contains one row with the version of twclient which created the
    database. This version string is stored to support future migrations,
    though none are supported now.

    Attributes
    ----------
    version
        The creating package version.
    '''

    version = Column(String(64), primary_key=True, nullable=False)


#
# Users, user tags and Twitter lists
#


@ut.export
class User(TimestampsMixin, FromTweepyInterface, Base):
    '''
    A Twitter user.

    This class and its associated user table represent attributes of a Twitter
    user which can't change over time. In practice, that means only user IDs -
    even screen names can change. See the UserData class and its user_data
    table for records of these mutable attributes.

    Attributes
    ----------
    user_id
        The Twitter user ID for this user. This ID is assigned at account
        creation and is stable for the lifetime of the account.
    '''

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


class StgUser(Base):
    '''
    A staging table for pulling exports.
    '''

    user_id = Column(BigInteger, primary_key=True, autoincrement=False)


@ut.export
class UserData(TimestampsMixin, FromTweepyInterface, Base):
    '''
    Mutable attributes of a Twitter user.

    This class and its associated user_data table represent records of a
    Twitter user's mutable attributes. Many API requests to Twitter send back
    user entities with various properties of a user, including things from
    screen names and verified status to follower counts; we store these
    entities here.

    Attributes
    ----------
    user_data_id
        An autoincrement ID for this fetch, not assigned by Twitter.

    user_id
        Twitter's user ID.

    url_id
        The user's profile URL (see the Url class).

    api_response
        The raw json text returned by Twitter.

    screen_name
        The user's screen name (note that this can change over time).

    create_dt
        The date and time the account was created.

    protected
        Does this account have protected tweets?

    verified
        Is this user verified?

    display_name
        The user's display name (not the screen name).

    description
        The user's bio text.

    location
        The user-provided free-form location field.

    friends_count
        The number of friends the user has (i.e., the number of other users
        they follow).

    followers_count
        The number of followers the user has.

    listed_count
        The number of lists the user appears on.
    '''

    user_data_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                          primary_key=True, autoincrement=True)

    user_id = Column(BigInteger,
                     ForeignKey('user.user_id', deferrable=True),
                     nullable=False, index=True)

    url_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('url.url_id', deferrable=True),
                    nullable=True, index=True)

    api_response = Column(UnicodeText, nullable=False)

    screen_name = Column(String(256), index=True, nullable=True)
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

    @staticmethod
    def _user_url(obj):
        url = None

        try:
            url = obj.entities['url']['urls'][0]['expanded_url']
        except (KeyError, IndexError):
            pass

        try:
            if url is None:
                url = obj.entities['url']['urls'][0]['display_url']
        except (KeyError, IndexError):
            pass

        try:
            if url is None:
                url = obj.entities['url']['urls'][0]['url']
        except (KeyError, IndexError):
            pass

        try:
            if url is None:
                url = obj.url
        except (KeyError, IndexError):
            pass

        return url

    @classmethod
    def from_tweepy(cls, obj, session=None):
        # Twitter sometimes includes NUL bytes, which might be handled
        # correctly by sqlalchemy + backend or might not: handling them is
        # risky. We'll just drop them to be safe.
        api_response = ut.tweepy_to_json(obj)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '') \
                                   .replace(r'\00', '').replace(r'\x00', '')

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

        for target, source in extra_fields.items():
            if hasattr(obj, source):
                args[target] = getattr(obj, source)

        ret = cls(**args)

        url = cls._user_url(obj)
        if url is not None:
            ret.url = Url.as_unique(session, url=url)

        return ret


@ut.export
class Tag(TimestampsMixin, Base):
    '''
    A tag that can be given to one or more Twitter users.

    This class represents a tag that can be applied to a set of Twitter users
    to help track them. Examples might include "treatment A", "journalists",
    "survey_respondents_2020", etc.

    Attributes
    ----------
    tag_id
        An autoincrement ID for the tag.

    name
        The name of the tag.
    '''

    tag_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(UnicodeText, nullable=False, unique=True)

    users = relationship('User', secondary=lambda: UserTag.__table__,
                         back_populates='tags')


@ut.export
class List(TimestampsMixin, FromTweepyInterface, Base):
    '''
    A Twitter list of users.

    Twitter allows users to create lists of other users, and represents these
    lists as first-class entities in its API. This class represents one of
    these lists (though not the users in it; see the UserList class for that).

    Attributes
    ----------
    list_id
        Twitter's ID for the list.

    user_id
        The Twitter user ID of the user who owns the list.

    slug
        The short name of the list (as it appears in, e.g., URLs).

    api_response
        The raw json text returned by Twitter.

    create_dt
        The date and time the list was created.

    full_name
        The list's "full name", which is its owning user's screen name (without
        the @ sign) and its slug, separated by a slash. For example,
        "cspan/members-of-congress".

    display_name
        The list's long-form display name, which may contain spaces and other
        characters which are not URL-safe.

    uri
        A resource URI for this list within the domain of Twitter entities.

    description
        A free-form bio/description text for the list.

    mode
        Either "public" or "private" depending on the visibility of the list.

    member_count
        The number of users on the list as of modified_dt.

    subscriber_count
        The number of users who subscribe to a public list (i.e., who have
        signed up to be able to view the combined timelines of the list
        members).
    '''

    # as in Tweet and User, list_id is Twitter's id rather than a surrogate key
    list_id = Column(BigInteger, primary_key=True, autoincrement=False)

    user_id = Column(BigInteger,
                     ForeignKey('user.user_id', deferrable=True),
                     nullable=False)  # no index needed given unique below

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
        api_response = ut.tweepy_to_json(obj)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '') \
                                   .replace(r'\00', '').replace(r'\x00', '')

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

        for target, source in extra_fields.items():
            if hasattr(obj, source):
                args[target] = getattr(obj, source)

        # other fields that take special handling
        if hasattr(obj, 'full_name'):
            args['full_name'] = obj.full_name[1:]

        return cls(**args)


@ut.export
class UserList(Base):
    '''
    User membership status for Twitter lists.

    This class represents a user's membership in a list, and records a user ID
    and a list ID. The underlying table is in type-2 SCD format, which means
    that the (user, list) edge is recorded together with the date it was
    observed (its validity start date). When it ceases to be observed (i.e., is
    missing on a fetch of the list members), the row is updated to add this
    validity end date. If the user subsequently returns to the list, a new row
    is added.

    Attributes
    ----------
    user_list_id
        An autoincrement row ID, not assigned by Twitter.

    user_id
        The Twitter user ID of the user who is a list member.

    list_id
        The Twitter list ID.

    valid_start_dt
        The SCD validity start date.

    valid_end_dt
        The SCD validity end date (None / NULL if the row is current).
    '''

    user_list_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                          primary_key=True, autoincrement=True)

    user_id = Column(BigInteger,
                     ForeignKey('user.user_id', deferrable=True),
                     nullable=False)  # no index needed given unique below

    list_id = Column(BigInteger,
                     ForeignKey('list.list_id', deferrable=True),
                     nullable=False, index=True)

    valid_start_dt = Column(TIMESTAMP(timezone=True), nullable=False,
                            server_default=func.now())
    valid_end_dt = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'list_id', 'valid_end_dt',
                         'valid_start_dt'),
    )

    lst = relationship('List', back_populates='list_memberships')
    user = relationship('User', back_populates='list_memberships')


@ut.export
class UserTag(TimestampsMixin, Base):
    '''
    Users who have been assigned tags.

    This table records the assignment of user tags (the Tag class) to users.

    Attributes
    ----------
    user_tag_id
        An autoincrement row ID.

    user_id
        The Twitter user ID of the user assigned a tag.

    tag_id
        The ID of the tag the user is assigned.
    '''

    user_tag_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                         primary_key=True, autoincrement=True)

    user_id = Column(BigInteger,
                     ForeignKey('user.user_id', deferrable=True),
                     nullable=False)  # no index needed given unique below

    tag_id = Column(Integer,
                    ForeignKey('tag.tag_id', deferrable=True),
                    nullable=False, index=True)

    __table_args__ = (UniqueConstraint('user_id', 'tag_id'),)


#
# Follow graph
#


@ut.export
class Follow(Base):
    '''
    The Twitter follow graph.

    This class records an edge in the Twitter follow graph. The underlying
    table stores these edges in a type-2 SCD format, which means that the
    (source_user, target_user) edge is recorded together with the date it was
    observed (its validity start date). When it ceases to be observed (i.e., is
    missing on a fetch where it would be present if still valid), the row is
    updated to add this validity end date. If the follow relationship is
    subsequently observed again, a new row is added.

    Attributes
    ----------
    follow_id
        An autoincrement row ID, not assigned by Twitter.

    source_user_id
        The origin user for the directed follow edge (i.e., a user who follows
        the user given by target_user_id).

    target_user_id
        The destination user for the directed follow edge (i.e., a user who is
        followed by the user given by source_user_id).

    valid_start_dt
        The SCD validity start date.

    valid_end_dt
        The SCD validity end date (None / NULL if the row is current).
    '''

    follow_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                       primary_key=True, autoincrement=True)

    source_user_id = Column(BigInteger,
                            ForeignKey('user.user_id', deferrable=True),
                            nullable=False)

    target_user_id = Column(BigInteger,
                            ForeignKey('user.user_id', deferrable=True),
                            nullable=False)

    valid_start_dt = Column(TIMESTAMP(timezone=True), nullable=False,
                            server_default=func.now())
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


class StgFollow(Base):
    '''
    A staging table for the loading of follow-graph edges.
    '''

    source_user_id = Column(BigInteger, primary_key=True, autoincrement=False)
    target_user_id = Column(BigInteger, primary_key=True, autoincrement=False)


#
# Tweets and tweet entities
#


@ut.export
class Tweet(TimestampsMixin, FromTweepyInterface, Base):
    '''
    A tweet.

    This model represents a tweet posted on Twitter and ingested from its API.
    Several tweet properties are normalized from the raw json into database
    entities and/or foreign keys.

    Attributes
    ----------
    tweet_id
        The ID assigned by Twitter to this tweet. These IDs are sequential
        integers, so that tweets with higher numbers were posted later.

    user_id
        The Twitter user ID of the user posting the tweet.

    retweeted_status_id
        If this tweet is a retweet of another tweet, the ID of the retweeted
        tweet. Because Twitter's API returns the other tweet as well in such
        cases, this is stored in the database as a foreign key back to the
        tweet table, helping with graph analysis.

    quoted_status_id
        If this tweet is a quote tweet of another tweet, the ID of the quoted
        tweet. Because Twitter's API returns the other tweet as well in such
        cases, this is stored in the database as a foreign key back to
        the tweet table, helping with graph analysis.

    api_response
        The raw json text returned by Twitter.

    content
        The body of the tweet. This field may differ from what is observed in
        the web interface on Twitter.com. In particular, retweets are prepended
        with "RT @POSTING_USER" and links are rendered with t.co rather than
        any display URLs.

    create_dt
        The date and time the tweet was posted.

    in_reply_to_status_id
        If this tweet is a reply, the ID of the tweet it was in reply to. The
        Twitter API does not return an entity for a replied-to tweet, so this
        field is not a foreign key (and may reference tweets not in the tweet
        table).

    in_reply_to_user_id
        If this tweet is a reply, the ID of the user who posted the tweet it
        was in reply to. The Twitter API does not return an entity for a
        replied-to tweet, so this field is not a foreign key (and may refer to
        users not in the user table).

    lang
        The detected language of the tweet.

    source
        The platform from which the tweet was posted (iPhone, Android, desktop,
        etc).

    truncated
        Was the tweet text truncated at 140 characters? Should always be false,
        included for visibility.

    retweet_count
        The number of times this tweet was retweeted.

    favorite_count
        The number of times this tweet was favorited / liked.
    '''

    # as in User, this is the Twitter id rather than a surrogate key
    tweet_id = Column(BigInteger, primary_key=True, autoincrement=False)

    user_id = Column(BigInteger,
                     ForeignKey('user.user_id', deferrable=True),
                     nullable=False, index=True)

    retweeted_status_id = Column(BigInteger,
                                 ForeignKey('tweet.tweet_id', deferrable=True),
                                 nullable=True, index=True)

    quoted_status_id = Column(BigInteger,
                              ForeignKey('tweet.tweet_id', deferrable=True),
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

    user = relationship('User', foreign_keys=[user_id],
                        back_populates='tweets')

    retweet_of = relationship('Tweet', foreign_keys=[retweeted_status_id],
                              remote_side=[tweet_id])
    quote_of = relationship('Tweet', foreign_keys=[quoted_status_id],
                            remote_side=[tweet_id])

    user_mentions = relationship('UserMention', back_populates='tweet',
                                 cascade='all, delete-orphan')
    hashtag_mentions = relationship('HashtagMention', back_populates='tweet',
                                    cascade='all, delete-orphan')
    symbol_mentions = relationship('SymbolMention', back_populates='tweet',
                                   cascade='all, delete-orphan')
    url_mentions = relationship('UrlMention', back_populates='tweet',
                                cascade='all, delete-orphan')
    media_mentions = relationship('MediaMention', back_populates='tweet',
                                  cascade='all, delete-orphan')

    @classmethod
    def from_tweepy(cls, obj, session=None):
        # remove NUL bytes as above
        api_response = ut.tweepy_to_json(obj)
        api_response = api_response.replace('\00', '').replace(r'\u0000', '') \
                                   .replace(r'\00', '').replace(r'\x00', '')

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

        for name in extra_fields:
            if hasattr(obj, name):
                val = getattr(obj, name)
                args[name] = (val if val != 'null' else None)

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


@ut.export
class Hashtag(TimestampsMixin, UniqueMixin, Base):
    '''
    A hashtag.

    This class represents a hashtag used in a tweet. Hashtags are stored
    without their '#' prefix.

    Attributes
    ----------
    hashtag_id
        An autoincrement row ID, not assigned by Twitter.

    name
        The text of the hashtag.
    '''

    hashtag_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                        primary_key=True, autoincrement=True)

    name = Column(UnicodeText, nullable=False, unique=True)

    mentions = relationship('HashtagMention', back_populates='hashtag',
                            cascade_backrefs=False)


@ut.export
class Symbol(TimestampsMixin, UniqueMixin, Base):
    '''
    A ticker symbol as detected by Twitter.

    Twitter attempts to detect stock-ticker symbols when prefixed with a '$' (a
    "cashtag") and make them searchable on its service. The detection is crude
    and based on regular expressions, with no attempt to ensure the detected
    symbols are real ticker symbols. Such cashtags are represented by this
    class, stored without their leading '$'.

    Attributes
    ----------
    symbol_id
        An autoincrement row ID, not assigned by Twitter.

    name
        The text of the symbol / cashtag.
    '''

    symbol_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                       primary_key=True, autoincrement=True)

    name = Column(UnicodeText, nullable=False, unique=True)

    mentions = relationship('SymbolMention', back_populates='symbol',
                            cascade_backrefs=False)


@ut.export
class Url(TimestampsMixin, UniqueMixin, Base):
    '''
    A URL.

    This class represents a unique URL that appeared somewhere on Twitter. URLs
    are represented as a separate entity rather than multiple text fields to
    make it easier to track them across the many places they may appear.

    Attributes
    ----------
    url_id
        An autoincrement row ID, not assigned by Twitter.

    url
        The URL itself.
    '''

    url_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    primary_key=True, autoincrement=True)

    # NOTE there's no unique index here because URLs can be very long, too long
    # for many index implementations to handle. The URLs are semantically
    # unique and are kept unique at the application layer by the logic in
    # UniqueMixin. (That is, there's a unique_hash column which is the SHA-1
    # hash of the url value and is under a unique constraint. Application code
    # fetching URLs deduplicates them according to the unique_hash.) It would
    # also be good to have a CHECK constraint that the url column hashes to the
    # appropriate value, but we can't even consider doing that because standard
    # SQL doesn't provide SHA-1.
    url = Column(UnicodeText, nullable=False, unique=False)

    mentions = relationship('UrlMention', back_populates='url',
                            cascade_backrefs=False)
    user_data = relationship('UserData', back_populates='url',
                             cascade_backrefs=False)
    media = relationship('Media', back_populates='url',
                         cascade_backrefs=False)
    media_variants = relationship('MediaVariant', back_populates='url',
                                  cascade_backrefs=False)


@ut.export
class MediaType(TimestampsMixin, UniqueMixin, FromTweepyInterface, Base):
    '''
    The type of a media object in a tweet.

    Media objects in tweets can have several types: photo, video, and others.
    This table tracks the observed types of media.

    Attributes
    ----------
    media_type_id
        An autoincrement row ID, not assigned by Twitter.

    name
        Twitter's name for this type of media.
    '''

    media_type_id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(UnicodeText, nullable=False, unique=True)

    media = relationship('Media', back_populates='media_type',
                         cascade_backrefs=False)

    @classmethod
    def from_tweepy(cls, obj, session=None):
        media_type = obj['type']
        if 'additional_media_info' in obj.keys():
            if 'embeddable' in obj['additional_media_info'].keys():
                if not obj['additional_media_info']['embeddable']:
                    media_type = 'unembeddable_video'

        return cls.as_unique(session, name=media_type)


@ut.export
class Media(TimestampsMixin, FromTweepyInterface, Base):
    '''
    A media object on Twitter.

    This class represents media objects like photos and videos which occur in
    tweets. The media's type and primary URL are recorded here. Note though
    that for videos the "primary" URL is a thumbnail still; see the
    MediaVariant class for the various video files actually available.

    Attributes
    ----------
    media_id
        Twitter's ID for this media.

    media_type_id
        The type of media.

    media_url_id
        The primary URL of the media. For videos, this URL is a thumbnail still
        and the video files themselves are recorded in the MediaVariant class.

    aspect_ratio_width
        For videos, the first number of the video's aspect ratio (e.g., "16"
        for a "16:9" aspect ratio). None / NULL otherwise.

    aspect_ratio_height
        For videos, the second number of the video's aspect ratio (e.g., "9"
        for a "16:9" aspect ratio). None / NULL otherwise.

    duration
        For videos, the duration of the video in seconds. None / NULL
        otherwise.
    '''

    # Twitter gives these IDs, so unlike with the other entities we don't have
    # to make one up
    media_id = Column(BigInteger,
                      primary_key=True, autoincrement=False)

    media_type_id = Column(Integer,
                           ForeignKey('media_type.media_type_id',
                                      deferrable=True),
                           nullable=False)

    media_url_id = Column(BigInteger,
                          ForeignKey('url.url_id', deferrable=True),
                          nullable=False)

    # video-specific attributes
    aspect_ratio_width = Column(Integer, nullable=True)
    aspect_ratio_height = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)

    media_type = relationship('MediaType', back_populates='media')
    url = relationship('Url', back_populates='media')
    variants = relationship('MediaVariant', back_populates='media',
                            cascade='all, delete-orphan')
    mentions = relationship('MediaMention', back_populates='media',
                            cascade_backrefs=False)

    @classmethod
    def from_tweepy(cls, obj, session=None):
        kwargs = {
            'media_id': obj['id']
        }

        # Info that's only populated for videos
        if 'video_info' in obj.keys():
            if 'duration_millis' in obj['video_info'].keys():
                duration = obj['video_info']['duration_millis']
                kwargs['duration'] = 0.001 * duration

            if 'aspect_ratio' in obj['video_info'].keys():
                width, height = obj['video_info']['aspect_ratio']

                kwargs['aspect_ratio_width'] = width
                kwargs['aspect_ratio_height'] = height

        return cls(**kwargs)


@ut.export
class MediaVariant(TimestampsMixin, ListFromTweepyInterface, Base):
    '''
    Specific video files for a Twitter video, which may have more than one.

    Twitter video media may have multiple specific video files associated with
    them, providing different bitrates, file formats or other properties. Each
    such video file is a MediaVariant.

    Attributes
    ----------
    media_id
        The Twitter media entity this video file is associated with.

    url_id
        The URL of the video file.

    bitrate
        The bitrate of the video file.

    content_type
        The MIME type of the video.
    '''

    media_id = Column(BigInteger,
                      ForeignKey('media.media_id', deferrable=True),
                      primary_key=True, autoincrement=False)

    url_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('url.url_id', deferrable=True),
                    primary_key=True, autoincrement=False)

    bitrate = Column(Integer, nullable=True)
    content_type = Column(UnicodeText, nullable=True)

    url = relationship('Url', back_populates='media_variants')
    media = relationship('Media', back_populates='variants',
                         cascade_backrefs=False)

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        ret = []

        if 'video_info' not in obj.keys():
            return ret

        if 'variants' not in obj['video_info'].keys():
            return ret

        for entity in obj['video_info']['variants']:
            kwargs = {
                'media_id': obj['id']
            }

            if 'bitrate' in entity.keys():
                kwargs['bitrate'] = entity['bitrate']

            if 'content_type' in entity.keys():
                kwargs['content_type'] = entity['content_type']

            variant = cls(**kwargs)
            variant.url = Url.as_unique(session, url=entity['url'])

            ret += [variant]

        return ret


@ut.export
class UserMention(TimestampsMixin, ListFromTweepyInterface, Base):
    '''
    A mention of a user in a tweet.

    This class represents a mention of a user in a tweet. There can be multiple
    mentions of the same user in the same tweet, so we also record the position
    in the tweet where the mention occurred.

    Attributes
    ----------
    tweet_id
        Twitter's ID for the tweet.

    start_index
        The index in the tweet content of the first character of this mention.

    end_index
        The index in the tweet content of the last character of this mention.

    mentioned_user_id
        The Twitter user ID of the user who was mentioned.
    '''

    tweet_id = Column(BigInteger,
                      ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)

    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    mentioned_user_id = Column(BigInteger,
                               ForeignKey('user.user_id', deferrable=True),
                               nullable=False, index=True)

    user = relationship('User', back_populates='mentions')
    tweet = relationship('Tweet', back_populates='user_mentions')

    __table_args__ = (
        UniqueConstraint('tweet_id', 'start_index', 'end_index'),
    )

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'user_mentions' in obj.entities.keys():
                for mtn in obj.entities['user_mentions']:
                    kwargs = {
                        'tweet_id': obj.id,
                        'start_index': mtn['indices'][0],
                        'end_index': mtn['indices'][1]
                    }

                    ret = cls(**kwargs)
                    ret.user = User(user_id=mtn['id'])

                    lst += [ret]

        return lst


@ut.export
class HashtagMention(TimestampsMixin, ListFromTweepyInterface, Base):
    '''
    A mention of a hashtag in a tweet.

    This class represents a mention of a hashtag in a tweet. There can be
    multiple mentions of the same hashtag in the same tweet, so we also record
    the position in the tweet where the mention occurred.

    Attributes
    ----------
    tweet_id
        Twitter's ID for the tweet.

    start_index
        The index in the tweet content of the first character of this mention.

    end_index
        The index in the tweet content of the last character of this mention.

    hashtag_id
        The (non-Twitter) ID of the hashtag that was mentioned.
    '''

    tweet_id = Column(BigInteger,
                      ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)

    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    hashtag_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                        ForeignKey('hashtag.hashtag_id', deferrable=True),
                        nullable=False, index=True)

    hashtag = relationship('Hashtag', back_populates='mentions')
    tweet = relationship('Tweet', back_populates='hashtag_mentions',
                         cascade_backrefs=False)

    __table_args__ = (
        UniqueConstraint('tweet_id', 'start_index', 'end_index'),
    )

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'hashtags' in obj.entities.keys():
                for mtn in obj.entities['hashtags']:
                    kwargs = {
                        'tweet_id': obj.id,
                        'start_index': mtn['indices'][0],
                        'end_index': mtn['indices'][1]
                    }

                    ret = cls(**kwargs)
                    ret.hashtag = Hashtag.as_unique(session, name=mtn['text'])

                    lst += [ret]

        return lst


@ut.export
class SymbolMention(TimestampsMixin, ListFromTweepyInterface, Base):
    '''
    A mention of a ticker symbol ("cashtag") in a tweet.

    This class represents a mention of a ticker symbol in a tweet. There can be
    multiple mentions of the same symbol in the same tweet, so we also record
    the position in the tweet where the mention occurred.

    Attributes
    ----------
    tweet_id
        Twitter's ID for the tweet.

    start_index
        The index in the tweet content of the first character of this mention.

    end_index
        The index in the tweet content of the last character of this mention.

    symbol_id
        The (non-Twitter) ID of the symbol that was mentioned.
    '''

    tweet_id = Column(BigInteger,
                      ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)

    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    symbol_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                       ForeignKey('symbol.symbol_id', deferrable=True),
                       nullable=False, index=True)

    symbol = relationship('Symbol', back_populates='mentions')
    tweet = relationship('Tweet', back_populates='symbol_mentions',
                         cascade_backrefs=False)

    __table_args__ = (
        UniqueConstraint('tweet_id', 'start_index', 'end_index'),
    )

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'symbols' in obj.entities.keys():
                for mtn in obj.entities['symbols']:
                    kwargs = {
                        'tweet_id': obj.id,
                        'start_index': mtn['indices'][0],
                        'end_index': mtn['indices'][1]
                    }

                    ret = cls(**kwargs)
                    ret.symbol = Symbol.as_unique(session, name=mtn['text'])

                    lst += [ret]

        return lst


@ut.export
class UrlMention(TimestampsMixin, ListFromTweepyInterface, Base):
    '''
    A mention of a URL in a tweet.

    This class represents a mention of a URL in a tweet. There can be
    multiple mentions of the same URL in the same tweet, so we also record
    the position in the tweet where the mention occurred. Some attributes of
    the URL mention itself, in addition to the URL, are also tracked here.

    Attributes
    ----------
    tweet_id
        Twitter's ID for the tweet.

    start_index
        The index in the tweet content of the first character of this mention.

    end_index
        The index in the tweet content of the last character of this mention.

    url_id
        The (non-Twitter) ID of the URL that was mentioned.

    twitter_short_url
        The t.co link that appears in the tweet body.

    twitter_display_url
        The display URL Twitter shows on its smartphone apps and desktop
        website.

    expanded_short_url
        If the user inputs an already shortened URL (e.g., bit.ly), Twitter
        resolves the URL further to a final page. In this case, we store the
        original short URL that the user entered here and use the resolved page
        as the main mentioned URL.

    status
        If a shortened URL input by a user was resolved further, the HTTP
        status code of the final GET request in the chain. None / NULL
        otherwise.

    title
        If a shortened URL input by a user was resolved further, the title of
        the fetched page. None / NULL otherwise.

    description
        If a shortened URL input by a user was resolved further, the value of
        the description meta tag for the fetched page. None / NULL otherwise.
    '''

    tweet_id = Column(BigInteger,
                      ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)

    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    url_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('url.url_id', deferrable=True),
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

    __table_args__ = (
        UniqueConstraint('tweet_id', 'start_index', 'end_index'),
    )

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        if hasattr(obj, 'entities'):
            if 'urls' in obj.entities.keys():
                for mtn in obj.entities['urls']:
                    kwargs = {
                        'tweet_id': obj.id,
                        'start_index': mtn['indices'][0],
                        'end_index': mtn['indices'][1]
                    }

                    if 'url' in mtn.keys():
                        kwargs['twitter_short_url'] = mtn['url']

                    if 'display_url' in mtn.keys():
                        kwargs['twitter_display_url'] = mtn['display_url']

                    if 'unwound' in mtn.keys():
                        kwargs['status'] = mtn['unwound']['status']
                        kwargs['title'] = mtn['unwound']['title']
                        kwargs['description'] = mtn['unwound']['description']

                        kwargs['expanded_short_url'] = mtn['expanded_url']
                        url = mtn['unwound']['url']
                    else:
                        url = mtn['expanded_url']

                    ret = cls(**kwargs)
                    ret.url = Url.as_unique(session, url=url)

                    lst += [ret]

        return lst


@ut.export
class MediaMention(TimestampsMixin, ListFromTweepyInterface, Base):
    '''
    A mention of a media object in a tweet.

    This class represents a mention of a media object like a photo or video in
    a tweet. There can be multiple mentions of the same media in the same
    tweet, so we also record the position in the tweet where the mention
    occurred. Some attributes of the media mention itself, in addition to the
    URL, are also tracked here.

    Attributes
    ----------
    tweet_id
        Twitter's ID for the tweet.

    start_index
        The index in the tweet content of the first character of this mention.

    end_index
        The index in the tweet content of the last character of this mention.

    media_id
        Twitter's ID for the media that was mentioned.

    twitter_short_url
        The t.co link that appears in the tweet body.

    twitter_display_url
        The display URL Twitter shows on its smartphone apps and desktop
        website.

    twitter_expanded_url
        The URL for the usual Twitter web viewer for this media, which one
        would encounter after clicking on it from Twitter.com.
    '''

    tweet_id = Column(BigInteger,
                      ForeignKey('tweet.tweet_id', deferrable=True),
                      primary_key=True, autoincrement=False)

    start_index = Column(Integer, primary_key=True, autoincrement=False)
    end_index = Column(Integer, primary_key=True, autoincrement=False)

    media_id = Column(BigInteger,
                      ForeignKey('media.media_id', deferrable=True),
                      nullable=False, index=True)

    # (Probably) properties of the specific media mention, not the media itself
    twitter_short_url = Column(UnicodeText, nullable=True)
    twitter_display_url = Column(UnicodeText, nullable=True)
    twitter_expanded_url = Column(UnicodeText, nullable=True)

    media = relationship('Media', back_populates='mentions')
    tweet = relationship('Tweet', back_populates='media_mentions',
                         cascade_backrefs=False)

    __table_args__ = (
        UniqueConstraint('tweet_id', 'start_index', 'end_index'),
    )

    @classmethod
    def list_from_tweepy(cls, obj, session=None):
        lst = []

        # the usual entities object provides incorrect information for media
        # entities; see Twitter's docs for the "extended entities" object
        if not hasattr(obj, 'extended_entities'):
            return lst

        if 'media' not in obj.entities.keys():
            return lst

        for mtn in obj.extended_entities['media']:
            #
            # The MediaMention object
            #

            kwargs = {
                'tweet_id': obj.id,
                'start_index': mtn['indices'][0],
                'end_index': mtn['indices'][1]
            }

            if 'url' in mtn.keys():
                kwargs['twitter_short_url'] = mtn['url']

            if 'display_url' in mtn.keys():
                kwargs['twitter_display_url'] = mtn['display_url']

            if 'expanded_url' in mtn.keys():
                kwargs['twitter_expanded_url'] = mtn['expanded_url']

            ret = cls(**kwargs)

            ret.media = Media.from_tweepy(mtn)
            ret.media.media_type = MediaType.from_tweepy(mtn, session)

            if 'media_url_https' in mtn.keys():
                media_url = mtn['media_url_https']
            else:
                media_url = mtn['media_url']
            ret.media.url = Url.as_unique(session, url=media_url)

            # "Variants" aka video files (multiple encodings per Media)
            ret.media.variants = MediaVariant.list_from_tweepy(mtn, session)

            lst += [ret]

        return lst
