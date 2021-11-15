-- follow graph
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
    uts.user_id as source_user_id,
    utt.user_id as target_user_id
from tmp_universe uts
    inner join follow fo on fo.source_user_id = uts.user_id
    inner join tmp_universe utt on utt.user_id = fo.target_user_id
where
    -- the follow table does type-2 SCD, so this condition says
    -- "only currently valid rows (not marked obsolete by a subsequent fetch)"
    fo.valid_end_dt is null;

