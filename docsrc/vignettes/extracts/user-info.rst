-- user info 

with tmp_universe as
(
    select
        u.user_id
    from "user" u
        inner join user_tag ut using(user_id)
        inner join tag ta using(tag_id)
    where
        ta.name = 'universe'
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

tmp_follower_count as
(
    select
        tu.user_id,
        count(*) as followers
    from tmp_universe tu
        inner join follow fo on fo.target_user_id = tu.user_id
    where
        fo.valid_end_dt is null
    group by 1
),

tmp_friend_count as
(
    select
        tu.user_id,
        count(*) as friends
    from tmp_universe tu
        inner join follow fo on fo.source_user_id = tu.user_id
    where
        fo.valid_end_dt is null
    group by 1
),

tmp_user_data as
(
    select
        i.user_id,
        i.screen_name,
        i.location,
        i.protected,
        i.verified,
        i.listed_count,
        i.account_create_dt
    from
    (
        select
            ud.user_id,

            ud.screen_name,
            ud.location,
            ud.protected,
            ud.verified,
            ud.listed_count,
            ud.create_dt as account_create_dt,

            -- this table is append-only, one new row for each call to "twitter
            -- fetch users", we only want the most recent one here
            row_number() over (
                partition by tu.user_id
                order by ud.insert_dt desc
            ) as rn
        from tmp_universe tu
            inner join user_data ud using(user_id)
    ) i
    where
        i.rn = 1
)
select
    tu.user_id,

    tud.account_create_dt,
    tud.protected,
    tud.verified,
    tud.listed_count,
    tud.screen_name,
    tud.location,

    coalesce(tfr.friends, 0) as friends,
    coalesce(tfo.followers, 0) as followers,

    coalesce(ttd.tweets_all_time, 0) as tweets_all_time,
    ttd.first_tweet_dt,
    ttd.last_tweet_dt,
    ttd.ios_user,
    ttd.android_user,
    ttd.desktop_user,
    ttd.business_app_user
from tmp_universe tu
    left join tmp_user_data tud on tud.user_id = tu.user_id
    left join tmp_friend_count tfr on tfr.user_id = tu.user_id
    left join tmp_follower_count tfo on tfo.user_id = tu.user_id
    left join tmp_tweet_data ttd on ttd.user_id = tu.user_id;

