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
    tw.tweet_id,

    uts.user_id as source_user_id,
    utt.user_id as target_user_id,

    tw.tweet_create_dt as reply_dt
from tmp_universe uts
    inner join twitter.tweet tw using(user_id)
    inner join tmp_universe utt on utt.user_id = tw.in_reply_to_user_id;

