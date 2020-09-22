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
    end as source_collapsed
from twitter.tweet tw
    inner join twitter.user u using(user_id)
    inner join twitter.user_tag ut using(user_id)
where
    ut.tag = 'universe' and

    tw.tweet_create_dt >=
    (
        select
            min(sn.start_dt)
        from radio.snippet_data sn
    ) and

    tw.tweet_create_dt <=
    (
        select
            max(sn.start_dt)
        from radio.snippet_data sn
    );

