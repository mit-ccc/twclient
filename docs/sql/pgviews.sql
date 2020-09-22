/*
 * Analytics views - some live, some materialized
 */

drop schema if exists analytics cascade;
create schema analytics;

create or replace view analytics.summary_stats_live as
with users as
(
    select
        count(*) as users_loaded,
        coalesce(sum((u.api_response is not null)::int), 0) as users_populated
    from twitter.user u
),

tweets as
(
    select
        count(*) as tweets_loaded,
        count(distinct user_id) as users_with_tweets
    from twitter.tweet
),

mentions as
(
    select
        count(*) as mentions_loaded,
        count(distinct mentioned_user_id) as users_mentioned
    from twitter.mention
),

follows as
(
    select
        count(*) as follow_graph_edges,
        count(distinct source_user_id) as users_with_friends,
        count(distinct target_user_id) as users_with_followers
    from twitter.follow
)

select
    *
from users
    cross join tweets
    cross join mentions
    cross join follows;

create or replace view analytics.all_mentions_live as
select
    tw.tweet_id,

    tw.user_id as source_user_id,
    mt.mentioned_user_id as target_user_id,

    extract(epoch from tw.tweet_create_dt) as currency_dt
from twitter.tweet tw
    inner join twitter.mention mt using(tweet_id);

create or replace view analytics.all_replies_live as
select
    tw.tweet_id,

    tw.user_id as source_user_id,
    tw.in_reply_to_user_id as target_user_id,

    extract(epoch from tw.tweet_create_dt) as currency_dt
from twitter.tweet tw;

drop materialized view if exists analytics.mention_graph_materialized;
create materialized view analytics.mention_graph_materialized as
select
    tw.user_id as source_user_id,
    mt.mentioned_user_id as target_user_id,

    count(*) as mentions,

    min(tw.tweet_create_dt) as first_dt,
    max(tw.tweet_create_dt) as last_dt
from twitter.tweet tw
    inner join twitter.mention mt using(tweet_id)
group by 1,2;

drop materialized view if exists analytics.reply_graph_materialized;
create materialized view analytics.reply_graph_materialized as
select
    tw.user_id as source_user_id,
    tw.in_reply_to_user_id as target_user_id,

    count(*) as replies,

    min(tw.tweet_create_dt) as first_dt,
    max(tw.tweet_create_dt) as last_dt
from twitter.tweet tw
group by 1,2;

create or replace function analytics.reply_graph_by_time(
    _start timestamp,
    _end timestamp
)
returns table (
    source_user_id bigint,
    target_user_id bigint,

    replies bigint,

    first_dt timestamp with time zone,
    last_dt timestamp with time zone
) as
$func$
select
    tw.user_id as source_user_id,
    tw.in_reply_to_user_id as target_user_id,

    count(*) as replies,

    min(tw.tweet_create_dt) as first_dt,
    max(tw.tweet_create_dt) as last_dt
from twitter.tweet tw
where
    tw.tweet_create_dt >= $1 and
    tw.tweet_create_dt <= $2
group by 1,2;
$func$ language sql;

create or replace function analytics.mention_graph_by_time(
    _start timestamp,
    _end timestamp
)
returns table (
    source_user_id bigint,
    target_user_id bigint,

    mentions bigint,

    first_dt timestamp with time zone,
    last_dt timestamp with time zone
) as
$func$
select
    tw.user_id as source_user_id,
    mt.mentioned_user_id as target_user_id,

    count(*) as mentions,

    min(tw.tweet_create_dt) as first_dt,
    max(tw.tweet_create_dt) as last_dt
from twitter.tweet tw
    inner join twitter.mention mt using(tweet_id)
where
    tw.tweet_create_dt >= $1 and
    tw.tweet_create_dt <= $2
group by 1,2;
$func$ language sql;

create or replace view analytics.tweets_live as
select
    tw.tweet_id,
    tw.user_id,

    regexp_replace(
        tw.content || coalesce(' ' || tw.quoted_status_content, ''),
        '[\n\r]+', ' ', 'g'
    ) as content,

    tw.tweet_create_dt,
    tw.lang,
    tw.source,
    tw.truncated,
    tw.retweeted_status_id is not null as is_retweet,
    tw.in_reply_to_status_id is not null as is_reply,
    tw.quoted_status_id is not null as is_quote_tweet,
    tw.retweet_count,
    tw.favorite_count,

    case tw.source
        when 'Twitter for iPhone' then 'iPhone'
        when 'Twitter for Android' then 'Android'
        when 'Twitter Web App' then 'Desktop'
        when 'Twitter Web Client' then 'Desktop'
        when 'TweetDeck' then 'Desktop'
        else 'Other'
    end as source_collapsed,

    tw.modified_dt as currency_dt
from twitter.tweet tw;

drop materialized view if exists analytics.tweet_activity_by_date_materialized;
create materialized view analytics.tweet_activity_by_date_materialized as
with
    tmp_date_range as
    (
        select
            min(tw.tweet_create_dt) as start_timestamp,
            max(tw.tweet_create_dt) as end_timestamp,

            min(tw.tweet_create_dt) as start_date,
            max(tw.tweet_create_dt) as end_date
        from twitter.tweet tw
    ),

    tmp_universe as
    (
        select
            u.user_id
        from twitter.user u
        where
            -- only manually loaded users, not e.g. those who are just followed
            -- by a user we're interested in
            u.api_response is not null
    ),

    tmp_user_date as
    (
        select
            tu.user_id,
            td.date
        from tmp_universe tu
            cross join dim.date td
            cross join tmp_date_range tdr
        where
            td.date >= tdr.start_date and
            td.date <= tdr.end_date
    ),

    tmp_tweet_stats_per_day as
    (
        select
            tu.user_id,
            date(tw.tweet_create_dt) as date,

            count(*) as tweets,
            count(tw.retweeted_status_id) as retweets,
            sum(tw.retweet_count) as retweeted,
            sum(tw.favorite_count) as liked
        from tmp_universe tu
            inner join twitter.tweet tw using(user_id)
        group by 1,2
    ),

    tmp_mentions_per_day as
    (
        select
            tu.user_id,
            date(tw.tweet_create_dt) as date,

            count(*) as mentions
        from tmp_universe tu
            inner join twitter.tweet tw using(user_id)
            inner join twitter.mention mt using(tweet_id)
        group by 1,2
    ),

    tmp_mentioned_per_day_universe as
    (
        select
            tu.user_id,
            date(tw.tweet_create_dt) as date,

            count(*) as mentioned_universe
        from tmp_universe tu
            inner join twitter.mention mt on mt.mentioned_user_id = tu.user_id
            inner join twitter.tweet tw using(tweet_id)
        group by 1,2
    ),

    tmp_replies_per_day as
    (
        select
            ut.user_id,
            date(tw.tweet_create_dt) as date,

            count(*) as replies
        from tmp_universe ut
            inner join twitter.tweet tw using(user_id)
        where
            tw.in_reply_to_user_id is not null
        group by 1,2
    ),

    tmp_replied_per_day_universe as
    (
        select
            ut.user_id,
            date(tw.tweet_create_dt) as date,

            count(*) as replied_universe
        from tmp_universe ut
            inner join twitter.tweet tw on tw.in_reply_to_user_id = ut.user_id
        group by 1,2
    ),

    tmp_account_ages as
    (
        select
            tud.user_id,
            tud.date,

            tud.date - date(u.account_create_dt) as account_age_in_days
        from tmp_user_date tud
            inner join twitter.user u using(user_id)
    ),

    tmp_days_since_last_tweet as
    (
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
        ) x
    )
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
    left join tmp_days_since_last_tweet tds using(user_id, date);

