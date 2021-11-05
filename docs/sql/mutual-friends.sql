-- this is just iteration in sql, it's straightforward but very slow if there
-- are either lots of users or esp users with lots of friends or esp esp both
-- because it's roughly O(n^2)

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
    ut1.user_id as user_id1,
    ut2.user_id as user_id2,

    (
        select
            count(*)
        from
        (
            select
                fo.target_user_id as user_id
            from follow fo
            where
                fo.valid_end_dt is null and
                fo.source_user_id = ut1.user_id

            intersect all

            select
                fo.target_user_id as user_id
            from follow fo
            where
                fo.valid_end_dt is null and
                fo.source_user_id = ut2.user_id
        ) x
    ) as mutual_friends
from tmp_universe ut1
    -- ">" general theta join rather than "=" equijoin because we don't want
    -- e.g. pair (123, 789) and also pair (789, 123), in particular because the
    -- query planner isn't very smart about this and it costs twice as much
    inner join tmp_universe ut2 on ut2.user_id > ut1.user_id;

