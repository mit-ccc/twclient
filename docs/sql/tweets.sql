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

    tw.create_dt,
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
from tmp_universe tu
    inner join tweet tw using(user_id)
    left join tweet twr on twr.tweet_id = tw.retweeted_status_id
    left join tweet twq on twr.tweet_id = tw.quoted_status_id
    left join tweet twp on twr.tweet_id = tw.in_reply_to_status_id;
-- or you might filter by, e.g, time:
-- where
    -- tw.tweet_create_dt >= '2020-03-13' and
    -- tw.tweet_create_dt <= '2020-05-14';

