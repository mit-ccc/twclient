========================================================
  Tweet-Derived Graphs: Mention, Reply, Retweet, Quote
========================================================

=================
  Mention graph
=================

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
        uts.user_id as source_user_id,
        utt.user_id as target_user_id,

        -- can also, e.g., group by time
        -- extract(year from tw.create_dt) as year,
        -- extract(month from tw.create_dt) as month,

        count(*) as num_mentions
    from tmp_universe uts
        inner join tweet tw using(user_id)
        inner join user_mention mt using(tweet_id)
        inner join tmp_universe utt on utt.user_id = mt.mentioned_user_id
    group by 1,2;

===============
  Reply graph
===============

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
        uts.user_id as source_user_id,
        utt.user_id as target_user_id,

        -- can also, e.g., group by time
        -- extract(year from tw.create_dt) as year,
        -- extract(month from tw.create_dt) as month,

        count(*) as num_replies
    from tmp_universe uts
        inner join tweet tw using(user_id)
        inner join tmp_universe utt on utt.user_id = tw.in_reply_to_user_id
    group by 1,2;

=================
  Retweet graph
=================

.. code-block:: sql

    -- this is ultimately from the "retweeted status" fields that come back on
    -- Twitter API responses; how it overlaps or doesn't with the quote graph
    -- from quoted_status_id (i.e. when a quote tweet is or isn't a retweet)
    -- depends on how Twitter defines and returns them in the API

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
        uts.user_id as source_user_id,
        utt.user_id as target_user_id,

        -- can also, e.g., group by time
        -- extract(year from tws.create_dt) as year,
        -- extract(month from tws.create_dt) as month,

        count(*) as num
    from tmp_universe uts
        inner join tweet tws on tws.user_id = uts.user_id
        inner join tweet twt on twt.tweet_id = tws.retweeted_status_id
        inner join tmp_universe utt on utt.user_id = twt.user_id
    group by 1,2;

===============
  Quote graph
===============

.. code-block:: sql

    -- this is ultimately from the "quoted status" fields that come back on Twitter
    -- API responses; how it overlaps or doesn't with the retweet graph from
    -- retweeted_status_id (i.e. when a quote tweet is or isn't a retweet) depends
    -- on how Twitter defines and returns them in the API

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
        uts.user_id as source_user_id,
        utt.user_id as target_user_id,

        -- can also, e.g., group by time
        -- extract(year from tws.create_dt) as year,
        -- extract(month from tws.create_dt) as month,

        count(*) as num
    from tmp_universe uts
        inner join tweet tws on tws.user_id = uts.user_id
        inner join tweet twt on twt.tweet_id = tws.quoted_status_id
        inner join tmp_universe utt on utt.user_id = twt.user_id
    group by 1,2;

