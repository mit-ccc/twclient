===============================================
  User-Level Information: Bio, Location, Etc.
===============================================

Along with tweets and follow graph edges, Twitter also provides some
information about each user. This information includes things like screen
names, self-reported location, short bio text, and others. We can :doc:`fetch
</vignettes/fetch>` this information with ``twclient fetch users ...`` and work
with it once fetched in ways described here.

Here's the simple way to get this data:

.. code-block:: sql

    select
        *
    from user_data;

To exclude columns like insertion and modification times that you might not be
interested in, we can instead list out columns:

.. code-block:: sql

    select
        user_id,

        screen_name,
        location,
        display_name,
        description,
        protected,
        verified,
        create_dt as account_create_dt
    from user_data;

Because user-provided URLs are normalized out, you need to join for them:

.. code-block:: sql

    select
        ud.user_id,

        u.url,
        ud.screen_name,
        ud.location,
        ud.display_name,
        ud.description,
        ud.protected,
        ud.verified,
        ud.create_dt as account_create_dt
    from user_data ud
        inner join url u using(url_id);

We can also add counts of the number of friends [1]_ and followers a user has,
as well as how many Twitter lists they've been placed on. Be aware, though that
these numbers are current only as of when the data was fetched. In particular,
they may not agree with:doc:`follow graph
</vignettes/sql-exports/follow-graph>` data.

.. code-block:: sql

    select
        ud.user_id,

        u.url,

        ud.friends_count,
        ud.followers_count,
        ud.listed_count,

        ud.screen_name,
        ud.location,
        ud.display_name,
        ud.description,
        ud.protected,
        ud.verified,
        ud.create_dt as account_create_dt
    from user_data ud
        inner join url u using(url_id);

The fact that each row in the ``user_data`` table reflects one particular fetch
of data means more than that certain counts may be out of date. It also means
that there may be more than one row per user; indeed :doc:`fetching
</vignettes/fetch>` this data multiple times can be a good way to keep track of
user friend and follower counts. To get only the most recent data for each
user, we need to use SQL's `window functions
<https://www.postgresql.org/docs/13/tutorial-window.html>`:

.. code-block:: sql

    select
        x.user_id,
        x.url,
        x.friends_count,
        x.followers_count,
        x.listed_count,
        x.screen_name,
        x.location,
        x.display_name,
        x.description,
        x.protected,
        x.verified,
        x.account_create_dt
    from
    (
        select
            ud.user_id,

            u.url,

            ud.friends_count,
            ud.followers_count,
            ud.listed_count,

            ud.screen_name,
            ud.location,
            ud.display_name,
            ud.description,
            ud.protected,
            ud.verified,
            ud.create_dt as account_create_dt,

            -- this table is append-only, one new row for each call to
            -- "twclient fetch users", we only want the most recent one here
            row_number() over (
                partition by tu.user_id
                order by ud.insert_dt desc
            ) as rn
        from user_data ud
            inner join url u using(url_id)
    ) x
    where
        x.rn = 1;

This query, while considerably longer, is not that much more complicated. It
displays a common pattern in SQL: use a window function in a subquery to select
a row (in this case, the row for each ``tu.user_id`` with the highest value of
``ud.insert_dt``, which is numbered with ``rn = 1``). We have to list the
columns again in the outermost query to avoid also selecting ``rn``.

Now, let's say we wanted to select this data only for a certain set of users,
such as those :doc:`tagged </vignettes/fetch>` with the tag named
"survey_respondents". We can start by figuring out how to select those
respondents at all. Working through the ``tag`` and ``user_tag`` tables, it
might look like this:

.. code-block:: sql

    select
        u.user_id
    from "user" u -- standard sql reserves this table name, need to quote it
        inner join user_tag ut using(user_id)
        inner join tag ta using(tag_id)
    where
        ta.name = 'survey_respondents';

We can restrict the query to only these respondents by using a temporary table
or a ``WITH`` statement and joining to it:

.. code-block:: sql

    with tmp_universe as
    (
        select
            u.user_id
        from "user" u
            inner join user_tag ut using(user_id)
            inner join tag ta using(tag_id)
        where
            ta.name = 'survey_respondents'
    )
    select
        x.user_id,
        x.url,
        x.friends_count,
        x.followers_count,
        x.listed_count,
        x.screen_name,
        x.location,
        x.display_name,
        x.description,
        x.protected,
        x.verified,
        x.account_create_dt
    from
    (
        select
            ud.user_id,

            u.url,

            ud.friends_count,
            ud.followers_count,
            ud.listed_count,

            ud.screen_name,
            ud.location,
            ud.display_name,
            ud.description,
            ud.protected,
            ud.verified,
            ud.create_dt as account_create_dt,

            row_number() over (
                partition by tu.user_id
                order by ud.insert_dt desc
            ) as rn
        from tmp_universe tu
            inner join user_data ud using(user_id)
            inner join url u using(url_id)
    ) x
    where
        x.rn = 1;

---------------------
  Adding tweet data
---------------------

Finally, we can illustrate the usefulness of databases and SQL here by asking
one more question: what if we wanted to add data about users' tweets to this
output? We can select a few basic variables about how each user uses Twitter
from the tweet table:

.. code-block:: sql

    select
        tw.user_id,

        count(*) as tweets_all_time,
        min(tw.create_dt) as first_tweet_dt,
        max(tw.create_dt) as last_tweet_dt,

        max((tw.source in ('Twitter for Android'))::int) as android_user,

        max((tw.source in ('Twitter for iPhone', 'Twitter for iPad', 'iOS',
                        'Tweetbot for iOS'))::int) as ios_user,

        max((tw.source in ('Twitter Web App', 'Twitter Web Client',
                        'TweetDeck', 'Twitter for Mac',
                        'Tweetbot for Mac'))::int) as desktop_user,

        max((tw.source in ('SocialFlow', 'Hootsuite', 'Hootsuite Inc.',
                        'Twitter Media Studio'))::int) as business_app_user
    from tweet tw
    group by 1;

Restrict them to the same "survey_respondents" universe as above:

.. code-block:: sql

    with tmp_universe as
    (
        select
            u.user_id
        from "user" u
            inner join user_tag ut using(user_id)
            inner join tag ta using(tag_id)
        where
            ta.name = 'survey_respondents'
    )
    select
        tu.user_id,

        count(*) as tweets_all_time,
        min(tw.create_dt) as first_tweet_dt,
        max(tw.create_dt) as last_tweet_dt,

        max((tw.source in ('Twitter for Android'))::int) as android_user,

        max((tw.source in ('Twitter for iPhone', 'Twitter for iPad', 'iOS',
                        'Tweetbot for iOS'))::int) as ios_user,

        max((tw.source in ('Twitter Web App', 'Twitter Web Client',
                        'TweetDeck', 'Twitter for Mac',
                        'Tweetbot for Mac'))::int) as desktop_user,

        max((tw.source in ('SocialFlow', 'Hootsuite', 'Hootsuite Inc.',
                        'Twitter Media Studio'))::int) as business_app_user
    from tmp_universe tu
        inner join tweet tw using(user_id)
    group by 1;

Note the inner join and the use of ``tu.user_id`` rather than ``tw.user_id`` in
the select list. This way we'll produce only rows for users who have at least
one recorded tweet; if you want rows for every user, including those with no
tweets, use a left join instead.

Finally, to avoid munging data in other, imperative language, we can combine
all these queries together and produce one user-level output file:

.. code-block:: sql

    with tmp_universe as
    (
        select
            u.user_id
        from "user" u
            inner join user_tag ut using(user_id)
            inner join tag ta using(tag_id)
        where
            ta.name = 'survey_respondents'
    ),

    tmp_tweet_data as
    (
        select
            tu.user_id,

            count(*) as tweets_all_time,
            min(tw.create_dt) as first_tweet_dt,
            max(tw.create_dt) as last_tweet_dt,

            max((tw.source in ('Twitter for Android'))::int) as android_user,

            max((tw.source in ('Twitter for iPhone', 'Twitter for iPad', 'iOS',
                            'Tweetbot for iOS'))::int) as ios_user,

            max((tw.source in ('Twitter Web App', 'Twitter Web Client',
                            'TweetDeck', 'Twitter for Mac',
                            'Tweetbot for Mac'))::int) as desktop_user,

            max((tw.source in ('SocialFlow', 'Hootsuite', 'Hootsuite Inc.',
                            'Twitter Media Studio'))::int) as business_app_user
        from tmp_universe tu
            inner join tweet tw using(user_id)
        group by 1
    ),

    tmp_user_data as
    (
        select
            x.user_id,
            x.url,
            x.friends_count,
            x.followers_count,
            x.listed_count,
            x.screen_name,
            x.location,
            x.display_name,
            x.description,
            x.protected,
            x.verified,
            x.account_create_dt
        from
        (
            select
                ud.user_id,

                u.url,

                ud.friends_count,
                ud.followers_count,
                ud.listed_count,

                ud.screen_name,
                ud.location,
                ud.display_name,
                ud.description,
                ud.protected,
                ud.verified,
                ud.create_dt as account_create_dt,

                row_number() over (
                    partition by tu.user_id
                    order by ud.insert_dt desc
                ) as rn
            from tmp_universe tu
                inner join user_data ud using(user_id)
                inner join url u using(url_id)
        ) x
        where
            x.rn = 1
    )
    select
        tu.user_id,

        tud.url,
        tud.friends_count,
        tud.followers_count,
        tud.listed_count,
        tud.screen_name,
        tud.location,
        tud.display_name,
        tud.description,
        tud.protected,
        tud.verified,
        tud.account_create_dt

        coalesce(ttd.tweets_all_time, 0) as tweets_all_time,
        ttd.first_tweet_dt,
        ttd.last_tweet_dt,
        ttd.android_user,
        ttd.ios_user,
        ttd.desktop_user,
        ttd.business_app_user
    from tmp_universe tu
        left join tmp_user_data tud on tud.user_id = tu.user_id
        left join tmp_tweet_data ttd on ttd.user_id = tu.user_id;

The final complication here is the use of ``coalesce(..., 0)`` in the select
list. Because we've left joined the ``tmp_user_data`` and ``tmp_tweet_data``
tables (and all tables are unique on ``user_id``), there will be one row in the
resultset for every row in ``tmp_universe``, even if it has no matching rows in
the other two tables. To avoid returning the resulting NULLs for the
``tweets_all_time`` column where having no tweets is a semantic 0, we replace
NULL with 0 via `COALESCE
<https://www.postgresql.org/docs/current/functions-conditional.html#FUNCTIONS-COALESCE-NVL-IFNULL>`.

And there you have it! User-level data from a script you're free to tweak and
re-use to your heart's content.

.. [1] "Friend" is Twitter's term for the opposite of a follower: if user A
   follows user B on Twitter, B is A's friend and A is B's follower.

