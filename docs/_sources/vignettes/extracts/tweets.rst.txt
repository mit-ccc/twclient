=================
  Users' Tweets
=================

One of the more obvious things to want to get out of the database is the tweets
users have posted. Tweets are the stuff of Twitter and usually an important
component of an analysis.

As with the :doc:`follow graph </vignettes/extracts/follow-graph>`, retrieving
tweets can be quick and simple or have some more bells and whistles. Here's the
simplest version:


.. code-block:: sql

   select
       *
   from tweet;

While appealingly short, this query will fetch some columns (like insertion and
modification times) that we don't want. A longer query for a smaller file might
go:

.. code-block:: sql

   select
       tweet_id, -- Twitter's ID for the tweet
       user_id, -- Twitter's ID for the user who posted it

       content, -- the tweet text

       -- is this tweet an RT?
       retweeted_status_id is not null as is_retweet,

       -- is this tweet a reply to another tweet?
       in_reply_to_status_id is not null as is_reply,

       -- is this tweet a QT of another tweet?
       quoted_status_id is not null as is_quote_tweet,

       create_dt, -- when the tweet was posted
       lang, -- Twitter's autodetected language of the tweet
       retweet_count, -- as of when we fetched the tweet
       favorite_count, -- as of when we fetched the tweet
       source -- the app or Twitter client with which the tweet was posted
   from tweet;

This query still leaves a few data formatting issues we could fix: the
``source`` field is unstandardized and the ``content`` field is totally
freeform text which can include newlines. These aren't hard to fix, though
(remember that we're using Postgres' dialect of SQL):

.. code-block:: sql

   select
       tweet_id,
       user_id,

       regexp_replace(content, '[\n\r]+', ' ', 'g') as content,

       retweeted_status_id is not null as is_retweet,
       in_reply_to_status_id is not null as is_reply,
       quoted_status_id is not null as is_quote_tweet,

       create_dt,
       lang,
       retweet_count,
       favorite_count,

       case source
           when 'Twitter for iPhone' then 'iPhone'
           when 'Twitter for Android' then 'Android'
           when 'Twitter Web App' then 'Desktop'
           when 'Twitter Web Client' then 'Desktop'
           when 'TweetDeck' then 'Desktop'
           else 'Other' -- you could of course code more of these
       end as source_collapsed
   from tweet;

What if you wanted to see the text of the retweeted, quoted or replied-to
statuses for those tweets which are RTs, QTs or replies? Just (left) join the
``tweet`` table to itself:

.. code-block:: sql

   select
       tw.tweet_id,
       tw.user_id,

       regexp_replace(tw.content, '[\n\r]+', ' ', 'g') as content,
       regexp_replace(twr.content, '[\n\r]+', ' ', 'g') as retweeted_status_content,
       regexp_replace(twq.content, '[\n\r]+', ' ', 'g') as quoted_status_content,
       regexp_replace(twp.content, '[\n\r]+', ' ', 'g') as in_reply_to_status_content,

       tw.retweeted_status_id is not null as is_retweet,
       tw.in_reply_to_status_id is not null as is_reply,
       tw.quoted_status_id is not null as is_quote_tweet,

       tw.create_dt,
       tw.lang,
       tw.retweet_count,
       tw.favorite_count,

       case tw.source
           when 'Twitter for iPhone' then 'iPhone'
           when 'Twitter for Android' then 'Android'
           when 'Twitter Web App' then 'Desktop'
           when 'Twitter Web Client' then 'Desktop'
           when 'TweetDeck' then 'Desktop'
           else 'Other'
       end as source_collapsed
   from tweet tw
       left join tweet twr on twr.tweet_id = tw.retweeted_status_id
       left join tweet twq on twr.tweet_id = tw.quoted_status_id
       left join tweet twp on twr.tweet_id = tw.in_reply_to_status_id;

It is worth noting that while we receive the IDs of retweeted, quoted or
replied-to statuses for all RTs, QTs and replies, Twitter's API returns full
tweet objects only for retweeted statuses. Accordingly this query may not
return text for quoted and replied-to statuses, even though there are IDs
recorded for them in the table. (This situation is reflected in the foreign-key
constraints on the ``tweet`` table: ``retweeted_status_id`` is a
self-referencing foreign key back to the ``tweet`` table, but the
``quoted_status_id`` and ``in_reply_to_status_id`` fields may be NULL.)

Finally, let's say we wanted to filter to only tweets posted by a certain
tagged set of users and within a certain period of time. As in the :doc:`follow
graph </vignettes/extracts/follow-graph>` vignette, you can achieve the first
with a join to a temporary table or `CTE
<https://www.postgresql.org/docs/14/queries-with.html>`__ and the second with a
WHERE-clause filter:

.. code-block:: sql

   with tmp_universe as
   (
       select
           u.user_id
       from "user" u -- standard sql reserves this table name, need to quote it
           inner join user_tag ut using(user_id)
           inner join tag ta using(tag_id)
       where
           -- just an example of using tagging, a tag
           -- with this name is not created automatically
           ta.name = 'universe'
   )
   select
       tw.tweet_id,
       tw.user_id,

       regexp_replace(tw.content, '[\n\r]+', ' ', 'g') as content,
       regexp_replace(twr.content, '[\n\r]+', ' ', 'g') as retweeted_status_content,
       regexp_replace(twq.content, '[\n\r]+', ' ', 'g') as quoted_status_content,
       regexp_replace(twp.content, '[\n\r]+', ' ', 'g') as in_reply_to_status_content,

       tw.retweeted_status_id is not null as is_retweet,
       tw.in_reply_to_status_id is not null as is_reply,
       tw.quoted_status_id is not null as is_quote_tweet,

       tw.create_dt,
       tw.lang,
       tw.retweet_count,
       tw.favorite_count,

       case tw.source
           when 'Twitter for iPhone' then 'iPhone'
           when 'Twitter for Android' then 'Android'
           when 'Twitter Web App' then 'Desktop'
           when 'Twitter Web Client' then 'Desktop'
           when 'TweetDeck' then 'Desktop'
           else 'Other'
       end as source_collapsed
   from tweet tw
       inner join tmp_universe tu on tu.user_id = tw.user_id
       left join tweet twr on twr.tweet_id = tw.retweeted_status_id
       left join tweet twq on twr.tweet_id = tw.quoted_status_id
       left join tweet twp on twr.tweet_id = tw.in_reply_to_status_id
   where
       tw.create_dt >= '2020-01-01' and
       tw.create_dt <= '2020-06-01';

