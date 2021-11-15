-- mention graph

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
    utt.user_id as target_user_id,

    -- can also, e.g., group by time
    -- extract(year from tw.create_dt) as year,
    -- extract(month from tw.create_dt) as month,

    count(*) as num_mentions
from tmp_universe uts
    inner join tweet tw using(user_id)
    inner join user_mention mt using(tweet_id)
    inner join tmp_universe utt on utt.user_id = mt.mentioned_user_id
group by 1,2;
