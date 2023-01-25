================================
  Mutual Followers and Friends
================================

One question that sometimes arises about a pair of Twitter users is how many
followers or friends [1]_ they have in common. There are several reasons you
might want to know this, including that it provides an indication of
between-user similarity. If you've :doc:`fetched </vignettes/fetch>`
follow-graph data, you can compute the number of mutual friends or followers
for a pair of users or all pairs of users in SQL.

How might we go about this? First, let's ask how to find the list of a user's
followers at all. Using user ID 123 for illustration, we might run this query,
where ``source_user_id`` means we're asking for the followers of
``target_user_id`` 123:

.. code-block:: sql

   select
       source_user_id as user_id
   from follow
   where
       valid_end_dt is null and
       target_user_id = 123;

Not too hard! Do note, though,  that in this query and throughout the rest of
this vignette, we'll consider only currently valid followers, not previously
valid follow edges which expired when one user unfollowed another. To implement
this restriction, various WHERE clauses will require that ``valid_end_dt is
null`` --- see the vignette on the :doc:`follow graph
</vignettes/sql-exports/follow-graph>` for more information.

But how do we get the subset of this group which also follows, say, user 456?
One way is to rely on SQL's ``INTERSECT`` feature, which calculates the set
intersection of two resultsets:

.. code-block:: sql

   select
       source_user_id as user_id
   from follow
   where
       valid_end_dt is null and
       target_user_id = 123

    intersect all

   select
       source_user_id as user_id
   from follow
   where
       valid_end_dt is null and
       target_user_id = 456;

We use ``INTERSECT ALL`` rather than ``INTERSECT`` because it's not necessary
to deduplicate the results: only one row can be marked valid for a given
(``source_user_id``, ``target_user_id``) pair at once.

Now, how would we get the count of how many users this query returns? Again,
it's not too big a leap: just use a subquery:

.. code-block:: sql

   select
       count(*) as cnt
   from
   (
       select
           source_user_id as user_id
       from follow
       where
           valid_end_dt is null and
           target_user_id = 123

        intersect all

       select
           source_user_id as user_id
       from follow
       where
           valid_end_dt is null and
           target_user_id = 456
   ) x;

What if we wanted to do this for every user in a specific set, such as those
tagged "universe"? (See the :doc:`fetching data vignette </vignettes/fetch>` for
a disucssion of the tagging feature.) We can retrieve the set of tagged users
as follows:

.. code-block:: sql

   select
       u.user_id
   from "user" u -- standard sql reserves this table name, need to quote it
       inner join user_tag ut using(user_id)
       inner join tag ta using(tag_id)
   where
       -- just an example of using tagging, a tag
       -- with this name is not created automatically
       ta.name = 'universe';

And combine it with the mutual-followers query above like this:

.. code-block:: sql

    with tmp_universe as
    (
        select
            u.user_id
        from "user" u
            inner join user_tag ut using(user_id)
            inner join tag ta using(tag_id)
        where
            ta.name = 'universe'
    )
    select
        ut1.user_id as user_id1,
        ut2.user_id as user_id2,

        (
            select
                count(*) as cnt
            from
            (
                select
                    fo.source_user_id as user_id
                from follow fo
                where
                    fo.valid_end_dt is null and
                    fo.target_user_id = ut1.user_id

                intersect all

                select
                    fo.source_user_id as user_id
                from follow fo
                where
                    fo.valid_end_dt is null and
                    fo.target_user_id = ut2.user_id
            ) x
        ) as mutual_followers
    from tmp_universe ut1
        inner join tmp_universe ut2 on ut1.user_id > ut2.user_id;

This query looks complicated but adds only one thing over the versions above.
The FROM clause generates all pairs of user IDs, unique up to order [2]_, and
the innermost pair of queries fed into the ``INTERSECT`` select the sets of
followers of each element in a given pair. (By referring to ``ut1.user_id`` and
``ut2.user_id`` rather than the specific values 123 and 456.) Because the
subquery that generates the count of mutual followers appears in the SELECT
list of columns, the one value it returns appears in the final resultset along
with the pair of user IDs it corresponds to.

This is an example of a `correlated
subquery <https://en.wikipedia.org/wiki/Correlated_subquery>`__. It's just
doing iteration in SQL: the DBMS executes the subquery once for each row in the
FROM clause, which is to say once for each pair of users, and concatenates the
results. Accordingly this query has to do :math:`O(n^2)` subqueries if there
are :math:`n` users, and may be quite slow, especially if some users have large
numbers of followers.

Finally, how would we change it to get the number of mutual friends? Simple:
just swap references to ``source_user_id`` and ``target_user_id``.

.. code-block:: sql

    with tmp_universe as
    (
        select
            u.user_id
        from "user" u
            inner join user_tag ut using(user_id)
            inner join tag ta using(tag_id)
        where
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
        inner join tmp_universe ut2 on ut1.user_id > ut2.user_id;

Only the innermost queries returning sets of followers (which are the arguments
to ``INTERSECT ALL``) have changed. We now select ``target_user_id`` and refer
to ``source_user_id`` in the WHERE clause, rather than the reverse.

.. [1] "Friend" is Twitter's term for the opposite of a follower: if user A
   follows user B on Twitter, B is A's friend and A is B's follower.

.. [2] That is, of the two pairs (123, 456) and (456, 123) we only want one of
   them, and so we arbitrarily pick the one in which the first element is
   larger (``ut1.user_id > ut2.user_id``). It's ">" rather than ">=" because
   there's no reason to ask how many followers a user has in common with
   themselves.
