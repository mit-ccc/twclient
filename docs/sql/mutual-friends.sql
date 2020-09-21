with tmp_radio as
(
    select
        u.user_id
    from twitter.user u
        inner join twitter.user_tag ut using(user_id)
    where
        ut.tag = 'radio'
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
            inner join tmp_radio tr using(user_id)
        where
            ff.is_friends
    ) x
    where
        x.rn = 1
)

select
    ut1.user_id as user_id1,
    ut2.user_id as user_id2,

    (
        select
            count(*)
        from
        (
            select
                fo.target_user_id as user_id
            from twitter.follow fo
                inner join tmp_last_follow_fetch ff using(follow_fetch_id)
            where
                fo.source_user_id = ut1.user_id

            intersect all

            select
                fo.target_user_id as user_id
            from twitter.follow fo
                inner join tmp_last_follow_fetch ff using(follow_fetch_id)
            where
                fo.source_user_id = ut2.user_id
        ) x
    ) as mutual_friends
from tmp_radio ut1
    inner join tmp_radio ut2 on ut2.user_id > ut1.user_id;

