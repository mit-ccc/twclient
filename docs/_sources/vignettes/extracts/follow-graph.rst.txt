=================
  Follow graph
=================

One of the most important pieces of Twitter data is the *follow graph* --- the
network among users where user A has a directed edge to user B if A follows B
on Twitter. Follow relationships shape which tweets people see, which other
users Twitter recommends they follow, and greatly affects their experience on
the site. Here we describe how to get the follow graph out of the twclient
database.

Without further ado, here's the simple version:

.. code-block:: sql

   select
       source_user_id,
       target_user_id
   from follow
   where
       -- the follow table does type-2 SCD, so this condition says
       -- "only currently valid rows (not marked obsolete by a subsequent fetch)"
       valid_end_dt is null;

As you can see, it isn't complicated. Directed edges are stored in the
``follow`` table, with the following user in the ``source_user_id`` column and
the followed user in the ``target_user_id`` column. Both columns are foreign
keys to the ``user`` table, ensuring that the graph is kept consistent with
records of users.

The only point which needs explanation is the WHERE clause. The ``follow``
table is stored in a `type-2 SCD
<https://en.wikipedia.org/wiki/Slowly_changing_dimension#Type_2:_add_new_row>`__
format, which minimizes the storage needed to handle repeated fetches of slowly
changing data like users' following lists. In this format, each row has start
and end validity dates: when a follow edge is first observed, its row is
created with ``valid_start_dt`` indicating when it was first observed and NULL
``valid_end_dt``, with the latter indicating that it is still valid. When it is
first *not* observed in a fetch where it should have been if it were still
valid, the row is updated to set ``valid_end_dt`` to the time the follow edge
was observed to be missing. Finally, if a follow relationship is first
observed, then some time later found to be missing, then observed again (say
because a user follows, unfollows and refollows another user), a new row is
created. Because most user don't regularly follow and unfollow large numbers of
other users, this format allows us to store repeated fetches of the follow
graph easily and with minimal space requirements.

You can also easily select your fetched follow graph *as it existed at a
particular time in the past*. The WHERE clause snippet in the example above ---
``where valid_end_dt is null`` --- asks for all currently valid rows, or the
most current state of the graph. But you can also get, for example, the follow
graph as you had recorded it six months ago:

.. code-block:: sql

   select
       source_user_id,
       target_user_id
   from follow
   where
       valid_start_dt < now() - interval '6 months' and
       (valid_end_dt >= now() - interval '6 months' or valid_end_dt is null);

That is, follow edges which were first observed more than six months ago, and
which either expired more recently than six months ago or whch are still valid.
Note that you need either of two conditions on ``valid_end_dt``: ``valid_end_dt
>= now() - interval '6 months'``, specifying follow edges which expired during
the last six months because one user was observed to have unfollowed the other,
and ``valid_end_dt is null`` to specify rows which are still valid.

It sounds obvious but is worth pointing out that this query will not give you
the *true* state of the follow graph six months ago, as recorded on Twitter's
servers, but only the version you had fetched. For example, if your last fetch
was seven months ago, six months ago your copy of the follow graph was a month
out of date, and that's the version this query will return.

Here's a slightly more complicated query which selects only follow edges
between a certain set of users---here, those with the "universe" tag. It
leverages the tagging feature explained in the :doc:`fetching data vignette
</vignettes/fetch>` and provides an example of how to use it:

.. code-block:: sql

   with tmp_universe as
   (
       select
           u.user_id
       from "user" u -- standard sql reserves this name, need to quote it
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
       fo.valid_end_dt is null;

