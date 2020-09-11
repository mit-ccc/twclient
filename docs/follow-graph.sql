with tmp_universe as
(
    select
        u.user_id
    from twitter.user u
        inner join twitter.user_tag ut using(user_id)
    where
        ut.tag = 'universe'
),

tmp_last_follow_fetch as
(
    select
        x.follow_fetch_id
    from
    (
        select
            ff.follow_fetch_id,

            row_number() over (
                partition by ff.user_id, ff.is_friends
                order by ff.insert_dt desc -- most recent
            ) as rn
        from twitter.follow_fetch ff
            inner join tmp_universe tu using(user_id)
    ) x
    where
        x.rn = 1
)

-- we're selecting distinct here because just using the most recent follow fetch
-- for each user and edge direction is not enough to ensure uniqueness of the
-- returned rows: if A follows B and we fetch A's friends and B's followers,
-- we'll get the edge A => B twice
select
    uts.user_id as source_user_id,
    utt.user_id as target_user_id
from tmp_universe uts
    inner join twitter.follow fo on fo.source_user_id = uts.user_id
    inner join tmp_last_follow_fetch tlf on tlf.follow_fetch_id = fo.follow_fetch_id
    inner join tmp_universe utt on utt.user_id = fo.target_user_id
group by 1,2;

