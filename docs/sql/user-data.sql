drop table if exists tmp_universe;
create local temporary table tmp_universe
on commit preserve rows as
select
    u.user_id
from twitter.user u
    inner join twitter.user_tag ut using(user_id)
where
    ut.tag = 'universe';

drop table if exists tmp_radio;
create local temporary table tmp_radio
on commit preserve rows as
select
    ut.user_id
from twitter.user_tag ut
where
    ut.tag = 'radio';

drop table if exists tmp_last_follow_fetch;
create local temporary table tmp_last_follow_fetch
on commit preserve rows as
select
    x.follow_fetch_id,
    x.is_friends,
    x.is_followers
from
(
    select
        ff.follow_fetch_id,
        ff.is_friends,
        ff.is_followers,

        row_number() over (
            partition by ff.user_id, ff.is_friends
            order by ff.insert_dt desc -- most recent
        ) as rn
    from twitter.follow_fetch ff
        inner join tmp_universe tu using(user_id)
) x
where
    x.rn = 1;

drop table if exists tmp_follower_count;
create local temporary table tmp_follower_count
on commit preserve rows as
select
    fo.target_user_id as user_id,
    count(*) as followers
from twitter.follow fo
    inner join tmp_last_follow_fetch ff using(follow_fetch_id)
where
    ff.is_followers
group by 1;

drop table if exists tmp_friend_count;
create local temporary table tmp_friend_count
on commit preserve rows as
select
    fo.source_user_id as user_id,
    count(*) as friends
from twitter.follow fo
    inner join tmp_last_follow_fetch ff using(follow_fetch_id)
where
    ff.is_friends
group by 1;

drop table if exists tmp_tweet_data;
create local temporary table tmp_tweet_data
on commit preserve rows as
select
    tu.user_id,

    count(*) as tweets_all_time,
    min(tw.tweet_create_dt) as first_tweet_dt,
    max(tw.tweet_create_dt) as last_tweet_dt,

    max((tw.source = 'Twitter for iPhone')::int) as iphone_user,
    max((tw.source = 'Twitter for Android')::int) as android_user,
    max((tw.source in ('Twitter Web App', 'Twitter Web Client',
                      'TweetDeck'))::int) as desktop_user
from tmp_universe tu
    inner join twitter.tweet tw using(user_id)
group by 1;

select
    tu.user_id,

    u.account_create_dt,
    u.protected,
    u.verified,

    coalesce(
        u.api_response->'favorites_count',
        u.api_response->'favourites_count'
    ) as likes_all_time,

    u.api_response->'listed_count' as listed_count,

    u.name,
    u.screen_name,
    u.description,
    u.location,
    u.url,

    tr.user_id is not null as is_radio,

    coalesce(tfr.friends, 0) as friends,
    coalesce(tfo.followers, 0) as followers,

    coalesce(ttd.tweets_all_time, 0) as tweets_all_time,
    ttd.first_tweet_dt,
    ttd.last_tweet_dt,
    ttd.iphone_user,
    ttd.android_user,
    ttd.desktop_user
from tmp_universe tu
    inner join twitter.user u using(user_id)
    left join tmp_radio tr on tr.user_id = tu.user_id
    left join tmp_friend_count tfr on tfr.user_id = tu.user_id
    left join tmp_follower_count tfo on tfo.user_id = tu.user_id
    left join tmp_tweet_data ttd on ttd.user_id = tu.user_id;

