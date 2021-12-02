========================================================
  Tweet-Derived Graphs: Mention, Reply, Retweet, Quote
========================================================

The :doc:`follow graph </vignettes/extracts/follow-graph>` isn't the only
useful graph structure in Twitter. There are several other graphs that connect
users, defined by their tweeting behavior. For example, the *mention graph* has
a (directed) edge from user A to user B if user A mentions user B in a tweet.
We'll look at four such graphs in total: mention, reply, retweet and quote.

Twclient preprocesses tweets on load into the database to make extracting these
graphs easier. User mentions as well as reply, retweet and quote relationships
between tweets are extracted into link tables or tweet attributes. For you,
trying to get the graphs out, that means simpler SQL.

-----------------
  Mention graph
-----------------

Without further ado, the mention graph:

.. code-block:: sql

    select
        tw.user_id as source_user_id,
        mt.mentioned_user_id as target_user_id,

        -- you can also, e.g., group by time
        -- extract(year from tw.create_dt) as year,
        -- extract(month from tw.create_dt) as month,

        count(*) as num_mentions
    from tweet tw
        inner join user_mention mt using(tweet_id)
    group by 1,2;

The ``user_mention`` table represents mentions of users in tweets. There's a
separate link table, rather than merely a key on the ``tweet`` table, because
one tweet can mention multiple users and indeed can mention the same user more
than once.

There are of course variations on this query: you can leave off the
``count(*)`` if the number of mentions isn't relevant, you can group by year,
month or other window of time during which tweets were posted, you can filter
by values of the tweet's ``create_dt`` in the WHERE clause, and so on.

---------------
  Reply graph
---------------

The *reply graph* has a directed edge from user A to user B if A replies to B's
tweet. It's even simpler to extract than the mention graph:

.. code-block:: sql

    select
        user_id as source_user_id,
        in_reply_to_user_id as target_user_id,

        count(*) as num_replies
    from tweet tw
    where
        in_reply_to_user_id is not null
    group by 1,2;

As with the mention graph, you can write plenty of variations on this query:
grouping by the time the tweet was posted, or filtering on such things as the
time the tweet was posted, the client it was posted from, or the language it
was written in. To filter by user-level properties like a user's verified
status, you'll need to join to the ``user_data`` table. To restrict to a
subgraph over a particular set of users, see below.

Note that the definition of reply used here and in the Twitter API is more
restrictive than what you can see in the Twitter.com web interface: you may
see "replying to A, B, C" when you post a reply, but your reply-tweet is still
in response to one specific tweet posted by one specific user (say, user B).
The ``in_reply_to_user_id`` field will (in this example) accordingly contain
user B's Twitter user ID.

It's also worth noting that in_reply_to_user_id may refer to a user not in the
``"user"`` table. This is because (unlike with retweets and quote tweets), the
Twitter API doesn't return the full text of the replied-to tweet with a reply.

-----------------
  Retweet graph
-----------------

The *retweet graph* has a directed edge from user A to user B if A retweets B's
tweet. Extracting it from the database relies on the ``retweeted_status_id``
column of the ``tweet`` table:

.. code-block:: sql

    select
        tws.user_id as source_user_id,
        twt.user_id as target_user_id,

        count(*) as num_retweets
    from tweet tws
        inner join tweet twt on twt.tweet_id = tws.retweeted_status_id
    group by 1,2;

Because the Twitter API does return the full text of the retweeted tweet along
with a retweet, we can join back to the ``tweet`` table to get the retweeted
user's ID.

---------------
  Quote graph
---------------

The *quote graph* has a directed edge from user A to user B if A quote-tweets
B's tweet. Similarly to how we can extract the retweet graph, getting the quote
graph out of the database relies on the ``tweet.quoted_status_id`` column:

.. code-block:: sql

    select
        tws.user_id as source_user_id,
        twt.user_id as target_user_id,

        count(*) as num_quote_tweets
    from tweet tws
        inner join tweet twt on twt.tweet_id = tws.quoted_status_id
    group by 1,2;

As with the retweet graph, the Twitter API returns the full text of quoted
tweets with the tweets that QT them, which allows us to join through ``tweet``
in constructing this graph.

------------------------------------------
  Filtering to a particular set of users
------------------------------------------

Frequently you won't want the mention graph over all users whose tweets you've
fetched, but only over some subset. If you've used the :doc:`tagging feature
</vignettes/fetch>` twclient provides for working with groups of users, you can
get the list of users tagged (for example) "influencers" as follows:

.. code-block:: sql

    select
        u.user_id
    from "user" u -- standard sql reserves this table name, need to quote
        inner join user_tag ut using(user_id)
        inner join tag ta using(tag_id)
    where
        ta.name = 'influencers';

Given this set of users, the trick is to join to it on the columns giving both
source and target user IDs:

.. code-block:: sql

    with tmp_universe as
    (
        select
            u.user_id
        from "user" u
            inner join user_tag ut using(user_id)
            inner join tag ta using(tag_id)
        where
            ta.name = 'influencers'
    )
    select
        uts.user_id as source_user_id,
        utt.user_id as target_user_id,

        count(*) as num_mentions
    from tmp_universe uts
        inner join tweet tw using(user_id)
        inner join user_mention mt using(tweet_id)
        inner join tmp_universe utt on utt.user_id = mt.mentioned_user_id
    group by 1,2;

We won't go through similar code snippets for the reply, retweet and quote
graphs, but you can use the same strategy of joining source and target user
columns to a list of users you want to restrict the graph to.

