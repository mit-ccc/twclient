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

This series of vignettes thus discusses how to extract certain commonly used
pieces of data from the database. These aren't by any means the only kinds of
data you may want to extract (there's nothing here about URLs, for instance),
but it covers the most common bases. The twclient package doesn't currently
provide direct support for extracting this sort of data, but that's the point
of using a database: you can just run some SQL.

We'll use the PostgreSQL dialect of SQL for examples here, but it isn't hard
to adapt the queries to the particular syntax of whatever DBMS you may be
using.

.. toctree::
   :maxdepth: 1
   :caption: SQL Examples:

   extracts/follow-graph.rst
   extracts/mention-graph.rst
   extracts/mutual-followers.rst
   extracts/mutual-friends.rst
   extracts/quote-graph.rst
   extracts/reply-graph.rst
   extracts/retweet-graph.rst
   extracts/tweets.rst
   extracts/user-info.rst

