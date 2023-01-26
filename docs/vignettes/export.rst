=============================
  Working with fetched data
=============================

Why go to the trouble of writing this package at all? The fundamental reason is
that, for analyzing data at least, it's easier to work with a relational
database than with a REST API. Local databases don't have rate limits, they
don't make you worry about pagination and cursoring, and they put all data in
one place for easy cross-referencing. More generally, using a database as this
package does *separates concerns*: the content is separate from the
presentation, and how you acquire and load Twitter data is decoupled from how
you choose to analyze it.

This series of vignettes thus discusses how to export certain commonly used
pieces of data from the database. These aren't by any means the only kinds of
data you may want to export (there's nothing here about URLs, for instance),
but it covers the most common bases.

There are two ways to get data out of the database: the ``twclient export``
command, and writing your own SQL.

~~~~~~~~~~~~~~~~~~~~
  Built-in exports
~~~~~~~~~~~~~~~~~~~~

You can export certain predefined bulk datasets with the ``twclient export``
command. The built-in exports cover the same datasets we present SQL for below:
the follow graph, tweets, tweet-derived graphs like the mention and reply
graphs, user-level information like location/bio/etc, and counts of mutual
followers or friends for user pairs. For more detail on exactly how these
datasets are defined, see the SQL examples and the included discussion of each
dataset.

Exporting data is simple: ``twclient export follow-graph`` will write the
follow graph to stdout; to specify an output file, use shell redirection or the
``-o`` flag. If you want to restrict the export to only certain users, you can
use the full set of user specification flags: ``-n`` to include certain screen
names, ``-i`` to include certain user IDs, ``-l`` to include one or more
Twitter lists, and ``-g`` to include one or more :doc:`tags you've created for
users </vignettes/fetch>`.

Here's a realistic example:

.. code-block:: bash

   twclient export mention-graph -o mention-graph.csv -g survey_respondents

For the full list of exportable datasets, run ``twclient export --help``.

~~~~~~~~~~~~~~
  Custom SQL
~~~~~~~~~~~~~~

Going the SQL route is more flexible if also somewhat more work. You'll need to
do this if you want to do much customization of the built-in exports. Of
course, allowing this sort of flexibility is the point of using a database
backend to store the Twitter data.

We'll use PostgreSQL's dialect of SQL for examples here, but it isn't much work
to adapt the queries to SQLite or whatever database you're using.

~~~~~~~~~~~~~~~~
  SQL Examples
~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2

   sql-exports/follow-graph.rst
   sql-exports/tweets.rst
   sql-exports/tweet-graphs.rst
   sql-exports/user-info.rst
   sql-exports/mutual-followers-friends-counts.rst
