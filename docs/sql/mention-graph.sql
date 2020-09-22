with tmp_universe as
(
    select
        u.user_id
    from twitter.user u
        inner join twitter.user_tag ut using(user_id)
    where
        ut.tag = 'universe'
)
select
    uts.user_id as source_user_id,
    utt.user_id as target_user_id,

    extract(year from tw.tweet_create_dt) as year,
    extract(month from tw.tweet_create_dt) as month,

    count(*) as mentions
from tmp_universe uts
    inner join twitter.tweet tw using(user_id)
    inner join twitter.mention mt using(tweet_id)
    inner join tmp_universe utt on utt.user_id = mt.mentioned_user_id
group by 1,2,3,4;

