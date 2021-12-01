'''
Classes encapsulating the "targets" of certain jobs.
'''

import logging

from abc import ABC, abstractmethod
from sqlalchemy import or_, and_, func

from . import models as md
from . import error as err
from . import _utils as ut

logger = logging.getLogger(__name__)


@ut.export
class Target(ABC):
    '''
    Encapsulate the notion of a "target" for certain kinds of jobs.

    Some of the operations defined by Job classes operate on users. These users
    can be specified in several ways (user IDs, screen names, tags stored in
    the database, Twitter lists) and the classes defined here provide a
    consistent interface for these various ways of specifying job targets. Each
    class takes a number of raw targets (user IDs, tags, etc) and provides a
    resolve() method that calculates the corresponding model.User objects.
    After calling resolve(), a list of the User objects are available in the
    .users attribute.

    Parameters
    ----------
        targets : list of str or int
            The raw targets to be resolved to users. These will be deduplicated
            in a way that preserves order.

        context : instance of job.Job, or None
            The Job instance's database and API connections will be used as
            needed to resolve raw targets to users. If not passed on
            initialization, a context object must be passed to ``resolve()``.

    Attributes
    ----------
        targets : list of str or int
            The list of raw targets passed in as the targets parameter, but
            deduplicated (without changing the relative order of any retained
            targets).
    '''

    def __init__(self, **kwargs):
        try:
            targets = kwargs.pop('targets')
        except KeyError as exc:
            raise ValueError('Must specify targets') from exc

        context = kwargs.pop('context', None)

        super().__init__(**kwargs)

        self._context = context

        self._users = []
        self._bad_targets = []
        self._missing_targets = []

        deduped = ut.uniq(targets)
        dupes = list(set(targets) - set(deduped))

        if dupes:
            msg = 'Deduping after following duplicate targets given: {0}'
            msg = msg.format(', '.join(dupes))
            logger.warning(msg)

        self.targets = deduped

        if self.resolved:
            self._validate_context(context)

        self._validate_targets()

    # This method is intended to be implemented by subclasses as
    # their main piece of logic, so the implementation on Target is abstract.
    @abstractmethod
    def resolve(self, context=None):
        '''
        Resolve this Target object into users.

        The resolve() method looks up the raw targets provided at self.targets
        and populates several attributes of this Target instance according to
        the resolve_mode set on the self.context object. The .good_targets,
        .bad_targets and .missing_targets attributes are populated to reflect
        dispositions of the raw targets, as discussed in their documentation,
        and the .users attribute contains all users which could be resolved
        from any of the raw targets. If no context parameter was passed to
        __init__, one must be given here. If one was passed to __init__, it is
        replaced with the value passed here so long as ``bool(context) ==
        True``.

        Parameters
        ----------
        context : job.Job object, or None
            The Job instance to use as context for resolving targets to users.

        Returns
        -------
        None
        '''

        raise NotImplementedError()

    @property
    @abstractmethod
    def allowed_resolve_modes(self):
        '''
        The resolve modes this Target implements.

        The Job instance referred to by self.context has a resolve_mode
        attribute, specifying how it wants Targets to look up their users. The
        allowed_resolve_modes attribute declares what resolve_mode values this
        Target instance can handle; if a Job instance with an incompatible
        resolve_mode is given as context, an error will be raised. This
        attribute must be defined in subclasses, because different types of
        targets are compatible or not with different values of this parameter.
        Consequently the version on Target is abstract.
        '''

        raise NotImplementedError()

    @property
    def resolved(self):
        '''
        Has this Target been set up with a Job instance as context?

        A Target instance can only resolve its users and make them available in
        the .users attribute after being given a Job instance as context. This
        attribute is True if the Target has a context and false otherwise.
        '''

        return self._context is not None

    @property
    def users(self):
        '''
        The users resolved from this Target's raw targets.

        The users attribute contains a list of the models.User attributes
        resolved from the raw targets (user IDs, screen names, Twitter lists
        or tags) passed to this Target instance. If no raw targets could be
        resolved to a models.User instance, this attribute will be an empty
        list. Note that raw targets may fail to resolve because they are not
        found in the database, if context.resolve_mode requires users to
        be loaded already, or because Twitter's API returns no users or raises
        an error. Note also that accessing this attribute before calling
        resolve() will raise AttributeError.
        '''

        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._users

    @property
    def bad_targets(self):
        '''
        Raw targets which were supposed to be looked up via the Twitter API
        and which, on doing so, were found not to exist.

        Specifically, these bad targets are users which were not returned by
        users/lookup (indicating that they are suspended, nonexistent, or
        otherwise bad), or lists which cause lists/show to raise an error. A
        list which exists but has no members is not an error. Note that a
        list not existing does not indicate for sure whether the owning user
        exists. Accessing this attribute before calling .resolve() will raise
        AttributeError.
        '''

        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._bad_targets

    @property
    def missing_targets(self):
        '''
        Raw targets which were supposed to be found in the database but were
        not there.

        These bad targets may be users which are not present in the user
        table, or lists which are not found in the list table. Note that a list
        not being present in the database does not indicate for sure whether
        the owning user is. Accessing this attribute before calling .resolve()
        will raise AttributeError.
        '''

        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._missing_targets

    @property
    def good_targets(self):
        '''
        Raw targets which were successfully resolved to users, either in the
        database or via the Twitter API.

        These are targets which, depending on the context object's setting of
        resolve_mode, may have been looked for in the database or via Twitter's
        API, and were found without error. Note that .good_targets and .users
        are different: if one target is, for example, the Twitter list named
        "cspan/members-of-congress", that value will appear in .good_targets
        and several hundred models.User objects for the Congressional Twitter
        accounts will appear in .users. Accessing this attribute before
        calling .resolve() will raise AttributeError.
        '''

        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return list(
            set(self.targets) -
            set(self.bad_targets) -
            set(self.missing_targets)
        )

    @property
    def context(self):
        '''
        The Job instance to be used as context by resolve().

        The resolve() method can only look up users with a Job instance as
        context, to support database lookups and Twitter API calls. The context
        can be provided on initialization or as an argument to resolve().
        '''

        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        return self._context

    # A stub for subclasses
    def _validate_targets(self):
        pass

    def _validate_context(self, context):
        if context.resolve_mode not in self.allowed_resolve_modes:
            raise ValueError('Bad operating mode for resolve()')

    def _mark_resolved(self, context):
        self._validate_context(context)
        self._context = context

    def _add_users(self, users):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        self._users.extend([u for u in users if u not in self._users])

    def _add_bad_targets(self, targets):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        if set(targets) - set(self.targets):
            raise ValueError('All bad targets must be in self.targets')

        self._bad_targets.extend(targets)

    def _add_missing_targets(self, targets):
        if not self.resolved:
            raise AttributeError('Must call resolve() first')

        if set(targets) - set(self.targets):
            raise ValueError('All missing targets must be in self.targets')

        self._missing_targets.extend(targets)

    def _tweepy_to_user(self, obj):
        user = md.User.from_tweepy(obj, self.context.session)
        self.context.session.merge(user)

        data = md.UserData.from_tweepy(obj, self.context.session)
        self.context.session.add(data)

        return user

    # splitting this out from _hydrate_users simplifies TwitterListTarget
    def _hydrate_sub(self, user_ids=None, screen_names=None):
        user_ids = ut.coalesce(user_ids, [])
        screen_names = ut.coalesce(screen_names, [])

        try:
            assert bool(user_ids) ^ bool(screen_names)
        except AssertionError as exc:
            raise ValueError('Must provide user_ids xor screen_names') from exc

        twargs = {'user_ids': user_ids, 'screen_names': screen_names}
        objs = list(self.context.api.lookup_users(**twargs))

        users = [self._tweepy_to_user(u) for u in objs]

        # NOTE tweepy's lookup_users doesn't raise an exception on bad users,
        # it just doesn't return them, so we need to check the length of the
        # input and the number of user objects returned.
        if user_ids:
            requested = user_ids
            received = [u.id for u in objs]
        else:  # screen_names
            requested = [sn.lower() for sn in screen_names]
            received = [u.screen_name.lower() for u in objs]

        bad_targets = list(set(requested) - set(received))
        bad_targets = [sn for sn in screen_names if sn.lower() in bad_targets]

        return users, bad_targets

    def _hydrate_users(self, user_ids=None, screen_names=None):
        if user_ids is None:
            user_ids = []

        if screen_names is None:
            screen_names = []

        users, bad_targets = self._hydrate_sub(
            user_ids=user_ids,
            screen_names=screen_names
        )

        self._add_users(users)
        self._add_bad_targets(bad_targets)

    def _user_for_screen_name(self, screen_name):
        user_data = self.context.session.query(md.UserData).filter(
            func.lower(md.UserData.screen_name) == screen_name.lower()
        ).order_by(
            md.UserData.user_data_id.desc()
        ).first()

        if user_data is None:
            ret = None
        else:
            ret = user_data.user

        return ret


@ut.export
class UserIdTarget(Target):
    '''
    A set of Twitter user IDs to resolve to users.

    This class takes targets specified by Twitter's numeric user IDs. These
    targets are resolved to models.User objects in one of three ways,
    determined by the value of context.resolve_mode. If the resolve mode is
    'fetch', users are first looked up in the database, with any missing from
    the database looked up via Twitter's API. (No users will be in
    missing_targets in this case, only good_targets or bad_targets.) If the
    mode is 'hydrate', all users will be looked up via Twitter's API. If mode
    is 'skip', users not found in the database will not be looked up via
    Twitter API, and will be left in missing_targets. Any other resolve mode
    set on the context object will raise an error.
    '''

    allowed_resolve_modes = ('fetch', 'hydrate', 'skip')

    def resolve(self, context=None):
        if context:  # replace current context if there is one
            self._mark_resolved(context)
        elif self.resolved:
            pass  # we already have a context object
        else:  # not context and not self.resolved
            raise ValueError('No context object set and none provided')

        if context.resolve_mode == 'hydrate':
            self._hydrate_users(user_ids=self.targets)
        else:
            existing = self.context.session.query(md.User) \
                           .filter(md.User.user_id.in_(self.targets))
            new = list(set(self.targets) - {u.user_id for u in existing})

            self._add_users(existing)
            self._add_missing_targets(new)

            if new:
                if context.resolve_mode == 'fetch':
                    self._hydrate_users(user_ids=new)
                else:  # context.resolve_mode == 'skip'
                    logger.warning('Not all requested users are loaded')


@ut.export
class ScreenNameTarget(Target):
    '''
    A set of screen names to resolve to users.

    This class takes targets specified by Twitter screen names for users.
    These targets are resolved to models.User objects in one of three ways,
    determined by the value of context.resolve_mode. If the resolve mode is
    'fetch', users are first looked up in the database, with any missing from
    the database looked up via Twitter's API. (No users will be in
    missing_targets in this case, only good_targets or bad_targets.) If the
    mode is 'hydrate', all users will be looked up via Twitter's API. If mode
    is 'skip', users not found in the database will not be looked up via
    Twitter API, and will be left in missing_targets. Any other resolve mode
    set on the context object will raise an error.
    '''

    allowed_resolve_modes = ('fetch', 'hydrate', 'skip')

    def resolve(self, context=None):
        if context:  # replace current context if there is one
            self._mark_resolved(context)
        elif self.resolved:
            pass  # we already have a context object
        else:  # not context and not self.resolved
            raise ValueError('No context object set and none provided')

        if context.resolve_mode == 'hydrate':
            self._hydrate_users(screen_names=self.targets)
        else:
            users = [self._user_for_screen_name(s) for s in self.targets]

            existing = [u for u in users if u is not None]
            new = [sn for u, sn in zip(users, self.targets) if u is None]

            self._add_users(existing)
            self._add_missing_targets(new)

            if new:
                if context.resolve_mode == 'fetch':
                    self._hydrate_users(screen_names=new)
                else:  # context.resolve_mode == 'skip'
                    logger.warning('Not all requested users are loaded')


@ut.export
class SelectTagTarget(Target):
    '''
    A set of user tags to resolve to users.

    This class takes targets specified by user tags, as recorded in the
    user_tag table in the database. These tags are first looked up in the
    database and resolved to a list of user IDs. Any tags which do not exist in
    the database are added to the missing_targets attribute. The resulting list
    of user IDs is then resolved to models.User objects in one of two ways,
    determined by the value of context.resolve_mode. If the mode is 'hydrate',
    all users will be looked up via Twitter's API. If the mode is 'skip',
    users will be returned with the data stored for them in the database. Any
    other resolve mode set on the context object will raise an error.
    '''

    allowed_resolve_modes = ('hydrate', 'skip')

    def resolve(self, context=None):
        if context:  # replace current context if there is one
            self._mark_resolved(context)
        elif self.resolved:
            pass  # we already have a context object
        else:  # not context and not self.resolved
            raise ValueError('No context object set and none provided')

        filters = [md.Tag.name == tag for tag in self.targets]

        tags = self.context.session.query(md.Tag).filter(or_(*filters)).all()
        tag_names = [t.name for t in tags]

        new = list({t for t in self.targets if t not in tag_names})

        if new:
            msg = 'Requested tag(s) {0} do not exist'
            msg = msg.format(', '.join(new))
            logger.warning(msg)

        self._add_missing_targets(new)

        users = [user for tag in tags for user in tag.users]
        if context.resolve_mode == 'hydrate':
            self._hydrate_users(user_ids=[user.user_id for user in users])
        else:  # context.resolve_mode == 'skip'
            self._add_users(users)


@ut.export
class TwitterListTarget(Target):
    '''
    A set of Twitter lists to resolve to users.

    This class takes Twitter lists as targets. These lists can be specified by
    their "full names" (that is, the owner_screen_name/slug format, like
    "cspan/members-of-congress") or by their numeric IDs. The list targets are
    resolved to models.User objects in one of three ways, determined by the
    value of context.resolve_mode. If the resolve mode is 'fetch', the lists
    are first looked up in the database, with any missing lists looked up via
    Twitter's API. (No lists will be in missing_targets in this case, only
    good_targets or bad_targets.) If the mode is 'hydrate', all lists will be
    looked up via Twitter's API. If mode is 'skip', lists not found in the
    database will not be looked up via Twitter API, and will be left in
    missing_targets. Any other resolve mode set on the context object will
    raise an error. Note that not only the users who are list members are
    stored, but also the list itself and its association with the users are
    added to the appropriate tables in the context object's database session.
    '''

    allowed_resolve_modes = ('fetch', 'hydrate', 'skip')

    def _validate_targets(self):
        fullnames = [obj for obj in self.targets if '/' in obj]
        ids = [obj for obj in self.targets if '/' not in obj]

        if len(fullnames) + len(ids) < len(self.targets):
            raise err.BadTargetError(message='Malformed list specification(s)')

        try:
            ids = [int(i) for i in ids]
        except ValueError as exc:
            msg = 'Malformed list specification(s)'
            raise err.BadTargetError(message=msg) from exc

    def _update_memberships(self, lst, members):
        # record user memberships in list
        new_uids = [u.user_id for u in members]
        prev_uids = [
            m.user_id
            for m in lst.list_memberships
            if m.valid_end_dt is None  # SCD type 2's currently valid rows
        ]

        # mark rows no longer in Twitter API's list as invalid
        for mem in lst.list_memberships:
            if mem.user_id not in new_uids:
                mem.valid_end_dt = func.now()

        # add rows for users newly present in Twitter API's list
        for user in members:
            if user.user_id not in prev_uids:
                self.context.session.add(md.UserList(
                    list_id=lst.list_id,
                    user_id=user.user_id
                ))

    def _hydrate_lists(self, lists):
        ids = [obj for obj in lists if '/' not in obj]
        fullnames = [obj for obj in lists if '/' in obj]

        if ids:
            self._hydrate_lists_ids(ids)

        if fullnames:
            self._hydrate_lists_fullnames(fullnames)

    def _hydrate_lists_ids(self, lists):
        for target in lists:
            try:
                twargs = {'list_id': int(target)}

                # Fetch the list itself
                resp = self.context.api.get_list(**twargs)
                owning_user = self._tweepy_to_user(resp.user)

                lst = md.List.from_tweepy(resp, self.context.session)
                lst.owning_user = owning_user

                # Fetch the list members from Twitter
                users = list(self.context.api.list_members(**twargs))
            except err.NotFoundError:
                # the bad targets are logged in the calling Job class
                self._add_bad_targets([target])
                continue
            else:
                lst = self.context.session.merge(lst)

                users = [self._tweepy_to_user(u) for u in users]
                self._add_users(users)

                self._update_memberships(lst, users)

    def _hydrate_lists_fullnames(self, lists):
        owner_screen_names = [obj.split('/')[0] for obj in lists]
        slugs = [obj.split('/')[1] for obj in lists]

        #
        # Hydrate the list owners
        #

        # _hydrate_sub doesn't raise NotFoundError on bad users because
        # lookup_users doesn't do so - no need to catch it
        owners, bad_owners = self._hydrate_sub(screen_names=owner_screen_names)

        #
        # Get list info and list members
        #

        for target, owner, slug in zip(lists, owners, slugs):
            if owner in bad_owners:
                self._add_bad_targets([target])
                continue

            try:
                twargs = {'slug': slug, 'owner_id': owner.user_id}

                # Fetch the list itself
                lst = self.context.api.get_list(**twargs)
                lst = md.List.from_tweepy(lst, self.context.session)

                # Fetch the list members from Twitter
                users = list(self.context.api.list_members(**twargs))
            except err.NotFoundError:
                # the bad targets are logged in the calling Job class
                self._add_bad_targets([target])
                continue
            else:
                lst = self.context.session.merge(lst)

                users = [self._tweepy_to_user(u) for u in users]
                self._add_users(users)

                self._update_memberships(lst, users)

    def resolve(self, context=None):
        if context:  # replace current context if there is one
            self._mark_resolved(context)
        elif self.resolved:
            pass  # we already have a context object
        else:  # not context and not self.resolved
            raise ValueError('No context object set and none provided')

        if context.resolve_mode == 'hydrate':
            self._hydrate_lists(self.targets)

        new = []
        for target in self.targets:
            try:
                if '/' in target:  # list "full name" e.g. "foxnews/hosts"
                    name = target.split('/')[0]
                    slug = target.split('/')[1]

                    owner = self._user_for_screen_name(name)

                    assert owner is not None  # caught below, list not ingested

                    lst = self.context.session.query(md.List).filter(and_(
                        md.List.user_id == owner.user_id,
                        md.List.slug == slug
                    )).one_or_none()
                else:  # target is Twitter's integer list ID
                    lst = self.context.session.query(md.List).filter(
                        md.List.list_id == int(target)
                    ).one_or_none()

                assert lst is not None  # also list not ingested
            except AssertionError:  # list hasn't been ingested
                self._add_missing_targets([target])

                if context.resolve_mode == 'fetch':
                    new += [target]
                else:  # context.resolve_mode == 'skip'
                    continue
            else:
                # every user currently recorded as a list member
                users = self.context.session.query(md.User).filter(
                    md.User.user_id.in_([
                        m.user_id
                        for m in lst.list_memberships
                        if m.valid_end_dt is None  # as above
                    ])
                )

                self._add_users(users)

        if context.resolve_mode == 'fetch' and new:
            self._hydrate_lists(new)
