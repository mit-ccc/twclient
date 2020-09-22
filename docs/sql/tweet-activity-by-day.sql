--
-- Preliminaries
--

drop table if exists tmp_period;
create local temporary table tmp_period
on commit preserve rows as
select
    date(min(sn.start_dt)) as start_date,
    date(max(sn.end_dt)) as end_date
from radio.snippet_data sn;

drop table if exists tmp_universe;
create local temporary table tmp_universe
on commit preserve rows as
select
    u.user_id
from twitter.user u
    inner join twitter.user_tag ut using(user_id)
where
    ut.tag = 'universe';

create or replace temporary view tmp_tweets as
select
    tw.*
from twitter.tweet tw
    cross join tmp_period tdr
where
    tw.tweet_create_dt >= tdr.start_date and
    tw.tweet_create_dt <= tdr.end_date;

drop table if exists tmp_user_date;
create local temporary table tmp_user_date
on commit preserve rows as
select
    tu.user_id,
    td.date,

    (
        td.date >= tdr.start_date and
        td.date <= tdr.end_date
    ) as in_snippet_window
from tmp_universe tu
    cross join tmp_period tdr
    cross join
    (
        -- all dates between start and end of snippet range
        select
            tdri.start_date - 100 + x.n as date
        from tmp_period tdri
            cross join
            (
                select
                    i1.n + 10*i2.n + 100 * i3.n as n
                from dim.integer i1
                    cross join dim.integer i2
                    cross join dim.integer i3
            ) x
        where
            x.n <= 100 + (tdri.end_date - tdri.start_date)
    ) td;

--
-- Data points
--

-- don't use the tmp_tweets view here: below, we need more days than
-- just the snippet window for computing days since last tweet
drop table if exists tmp_tweet_stats_per_day;
create local temporary table tmp_tweet_stats_per_day
on commit preserve rows as
select
    tu.user_id,
    date(tw.tweet_create_dt) as date,

    count(*) as tweets,
    count(tw.retweeted_status_id) as retweets,
    sum(tw.retweet_count) as retweeted,
    sum(tw.favorite_count) as liked
from tmp_universe tu
    inner join twitter.tweet tw using(user_id)
group by 1,2;

drop table if exists tmp_mentions_per_day;
create local temporary table tmp_mentions_per_day
on commit preserve rows as
select
    tu.user_id,
    date(tw.tweet_create_dt) as date,

    count(*) as mentions
from tmp_universe tu
    inner join tmp_tweets tw using(user_id)
    inner join twitter.mention mt using(tweet_id)
group by 1,2;

drop table if exists tmp_mentioned_per_day_universe;
create local temporary table tmp_mentioned_per_day_universe
on commit preserve rows as
select
    tu.user_id,
    date(tw.tweet_create_dt) as date,

    count(*) as mentioned_universe
from tmp_universe tu
    inner join twitter.mention mt on mt.mentioned_user_id = tu.user_id
    inner join tmp_tweets tw using(tweet_id)
group by 1,2;

drop table if exists tmp_replies_per_day;
create local temporary table tmp_replies_per_day
on commit preserve rows as
select
    ut.user_id,
    date(tw.tweet_create_dt) as date,

    count(*) as replies
from tmp_universe ut
    inner join tmp_tweets tw using(user_id)
where
    tw.in_reply_to_user_id is not null
group by 1,2;

drop table if exists tmp_replied_per_day_universe;
create local temporary table tmp_replied_per_day_universe
on commit preserve rows as
select
    ut.user_id,
    date(tw.tweet_create_dt) as date,

    count(*) as replied_universe
from tmp_universe ut
    inner join tmp_tweets tw on tw.in_reply_to_user_id = ut.user_id
group by 1,2;

drop table if exists tmp_account_ages;
create local temporary table tmp_account_ages
on commit preserve rows as
select
    tud.user_id,
    tud.date,

    tud.date - date(u.account_create_dt) as account_age_in_days
from tmp_user_date tud
    inner join twitter.user u using(user_id)
where
    tud.in_snippet_window;

drop table if exists tmp_days_since_last_tweet;
create local temporary table tmp_days_since_last_tweet
on commit preserve rows as
select
    x.user_id,
    x.date,
    x.tweeted_date,

    x.cce,

    first_value(x.tweeted_date) over (
        partition by x.user_id, x.cce
        order by x.date
    ) as most_recent_tweet_date,

    x.date - first_value(x.tweeted_date) over (
        partition by x.user_id, x.cce
        order by x.date
    ) as days_since_last_tweet
from
(
    select
        tud.user_id,
        tud.date,

        tts.date as tweeted_date,

        count(tts.date) over (
            partition by tud.user_id
            order by tud.date
        ) as cce
    from tmp_user_date tud
        left join tmp_tweet_stats_per_day tts using(user_id, date)
) x;

--
-- Roll it all up
--

select
    tud.user_id,
    tud.date,

    taa.account_age_in_days,

    coalesce(tts.tweets, 0) as tweets,
    coalesce(tts.retweets, 0) as retweets,
    coalesce(tts.retweeted, 0) as retweeted,
    coalesce(tts.liked, 0) as liked,

    coalesce(tms.mentions, 0) as mentions,
    coalesce(tmd.mentioned_universe, 0) as mentioned_universe,

    coalesce(trs.replies, 0) as replies,
    coalesce(trd.replied_universe, 0) as replied_universe,

    coalesce(tds.days_since_last_tweet, 100) as days_since_last_tweet
from tmp_user_date tud
    left join tmp_account_ages taa using(user_id, date)
    left join tmp_tweet_stats_per_day tts using(user_id, date)
    left join tmp_mentions_per_day tms using(user_id, date)
    left join tmp_mentioned_per_day_universe tmd using(user_id, date)
    left join tmp_replies_per_day trs using(user_id, date)
    left join tmp_replied_per_day_universe trd using(user_id, date)
    left join tmp_days_since_last_tweet tds using(user_id, date)
where
    tud.in_snippet_window;

