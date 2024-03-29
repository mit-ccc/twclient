=====================================
  Getting data from the Twitter API
=====================================

So you want to analyze some Twitter data. (That's why you're here, right?) This
vignette walks through how to get set up and how to acquire the data.

**Obligatory disclaimer / reminder**: You should comply with Twitter's terms of
service and respect user privacy. It's important to only access data you have a
right to access.

----------------
  Introduction
----------------

Twclient makes acquiring data easier than directly interacting with the Twitter
REST API, which you can do through a lightweight client like Twitter's own
`twurl <https://github.com/twitter/twurl>`__ or a more featureful package like
`tweepy <https://www.tweepy.org/>`__. Using either of these makes you do quite
a bit of work you'd rather avoid: thinking about cursoring and pagination of
results, manually handling multiple sets of credentials if you have more than
one, and of course munging data into the format you want. (No disrespect to
tweepy, of course: twclient uses it for low-level interactions with the Twitter
API.)

Data munging in particular is not a simple task. You may have to keep and
organize the raw json responses from Twitter's API, and then extract things
from them via a tool like `jq <https://stedolan.github.io/jq/>`__; if using
tweepy, you have to write some python code to serialize the User, Tweet, etc,
objects it produces to a format you can work with.

In general, of course, there's no way around this: if you want to write an
application like a Twitter client, which people can use to view their feeds,
post tweets, and whatever else, you need the API in its full complexity. But
here we have a simpler task---read-only scraping of data---and so we can make a
simpler tool. (For formatting that data and exporting it from the database,
see the :doc:`other vignette on exporting data </vignettes/export>`.)

Note that Twitter has other data sources than the REST API, in particular the
`PowerTrack
<https://developer.twitter.com/en/docs/twitter-api/enterprise/historical-powertrack-api/overview>`__
API, and this package does not support those. It also does not (yet) support
Twitter's new `v2 API <https://developer.twitter.com/en/docs/twitter-api>`__.

Enough talk! How do you get started?

In brief: This package provides a command-line interface for loading data from
the Twitter REST API into the database of your choice. You can invoke it as
``twclient``, as in ``twclient fetch users -n wwbrannon``. You need to get and
set up API credentials, set up your database, and then you can pull and work
with data.

-------------
  API setup
-------------

You can't get data from the Twitter API without API credentials, so the next
step is to get at least one set of credentials. If you don't already have
credentials, Twitter has `documentation
<https://developer.twitter.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api>`__
on how to get them.

You'll generally receive four pieces of `OAuth
<https://en.wikipedia.org/wiki/OAuth>`__ authentication information: a consumer
key, consumer secret, access token and access token secret. If using `OAuth 2.0
bearer tokens <https://oauth.net/2/bearer-tokens/>`__ you may receive only a
consumer key and consumer secret. Regardless, you can add them to twclient as
follows (replacing the "XXXXX" with your values, and omitting token and token
secret if using a bearer token):

.. code-block:: bash

   twclient config add-api -n twitter1 \
       --consumer-key XXXXX \
       --consumer-secret XXXXX \
       --token XXXXX \
       --token-secret XXXXX

Similarly to the database setup, this command stores the credentials in your
config file under an API profile named "twitter1" for ease of use. We've only
added one set of credentials here, but you can add arbitrarily many under
different names. Twclient will seamlessly switch between them as each one hits
rate limits.

------------------
  Database setup
------------------

Configuration
---------------

Next, you need to configure a database. The easy, low-effort way to do this is
to use a file-backed SQLite database. Because SQLite is built into Python and
doesn't have a separate server process, you don't need to install or configure
anything else to get started. Here's how:

.. code-block:: bash

   twclient config add-db -f /path/to/your/project/sqlite.db db

This command tells twclient to create a persistent profile for a database and
call it "db", with the database itself stored in SQLite format in the file you
specify. The database profile you create is stored in a twclient configuration
file, by default ``~/.twclientrc``, so that you don't need to keep
providing the database URL for each command.

Be aware, though, that if you want to interact with the database via SQL,
Python doesn't package a frontend shell or client. SQLite has a `standard
client <https://www.sqlite.org/index.html>`__ you can download, and you can
also install it from `Homebrew <https://brew.sh/>`__ (on a Mac) or your Linux
distribution's package manager.

SQLite is not the only database you can use: twclient can use any
database `supported by sqlalchemy
<https://docs.sqlalchemy.org/en/14/dialects/>`__. In addition to SQLite, We've
also tested with `Postgres <https://www.postgresql.org/>`__, which is used for
the SQL examples in the :doc:`data export vignette </vignettes/export>`. Do
note that while you can use other sqlalchemy-compatible databases, we've only
tested with SQLite and Postgres.

If you want to use Postgres, you'll need to do at least a bit of work to set up
the database. If you're on a Mac, `Postgres.app <https://postgresapp.com/>`__
is a highly user-friendly distribution of Postgres. It's not the only one:
among others you can download the database from `its website
<https://www.postgresql.org/>`__, use `Amazon RDS
<https://aws.amazon.com/rds/>`__, or `run it with Docker
<https://hub.docker.com/_/postgres>`__.

You can configure twclient to use a Postgres database (that you've already set
up) as follows:

.. code-block:: bash

   twclient config add-db -u "postgresql:///" postgres

The only new thing here is that, instead of a single file passed to the ``-f``
option, we have a `sqlalchemy connection URL
<https://docs.sqlalchemy.org/en/14/core/engines.html#database-urls>`__ and the
``-u`` option. (``-f`` is syntactic sugar for sqlalchemy's SQLite URL format.)

The specific URL here, ``postgresql:///``, indicates the default
database on a Postgres server accessed through the default local Unix socket,
with trust/passwordless authentication, using sqlalchemy's default Postgres
driver. (If you're using Postgres.app on a Mac, this is likely the URL you want
to use.)

Installing Data Model
-----------------------

Next up, we have to install the data model: create the tables, columns, keys
and other DB objects the twclient package uses. Be aware that doing this will
**drop all existing twclient data in your database**. The ``twclient
initialize`` command will do the trick, but to confirm that you understand
running it will **drop all existing twclient data in your database** you have
to specify the ``-y`` flag:

.. code-block:: bash

   # if you've configured more than one database with `twclient config add-db`,
   # pass the `-d` option to specify which one to initialize
   twclient initialize -y

And that's it! If you fire up a database client you'll see a new database
schema installed. The tables, columns and other objects are documented, in the
form of their sqlalchemy model classes, in the API documentation for
twclient.models.

-------------------------
  Actually pulling data
-------------------------

Now comes the fun part: actually downloading some data. We'll assume you've
pulled together sets of Twitter users and `Twitter lists
<https://help.twitter.com/en/using-twitter/twitter-lists>`__ you want to
retrieve information on. This example will use the following two files, one
each of individual users and lists of users. (The usernames, user IDs and lists
are fake for privacy reasons, so replace them with real ones if you want to run
this.)

Here's ``users.csv``:

::

   screen_name
   user1
   user2
   user3
   test1234
   foobar
   stuff

And here's ``lists.csv``:

::

   list
   myaccount/mylist
   2389231097
   18230127
   big_newspaper/reporters
   20218236
   1937309
   1824379139

A word about identifiers
--------------------------

In general, Twitter allows you to refer to a user or list by either a) a
numeric user ID or list ID, or b) a human-readable name. Readable names for
users are called screen names, and for lists are called "full names." List full
names consist of the screen name of the user who owns the list and a
list-specific slug, separated by a slash. (For example,
"cspan/members-of-congress".)

With twclient, you can mix numeric and human-readable names for lists, as in
``lists.csv`` above, but not for users. That is, you could instead use this
``users_alternative.csv``:

::

   user_id
   137923923763
   37480133935
   237290537913
   3784935713
   3096490427891
   612092404590

but not one file which mixes user IDs and screen names together. This is
because of the way the underlying Twitter API endpoints are implemented:
They'll accept mixed references to lists, but not to users.

Hydrating users
-----------------

The first step is to `hydrate
<https://stackoverflow.com/questions/34191022/what-does-hydrate-mean-on-twitter/34192633>`__
the target users, which confirms with the Twitter API that they exist,
retrieves some summary information about them and creates records for them in
the database. You can do this with the ``twclient fetch`` family of commands,
and specifically ``twclient fetch users``. We'll start by fetching the users in
the lists of ``lists.csv``, though you could do the individual users first:

.. code-block:: bash

   tail -n +2 lists.csv | xargs twclient fetch users -v -b -l

This command skips the CSV header line (via ``tail -n +2 lists.csv``), which
twclient doesn't actually use, and pipes the rest of it to ``twclient fetch -v
users -b -l`` via ``xargs``. The ``-v`` flag requests verbose output, ``-b``
says to continue even if the Twitter API says some of the lists requested are
protected or don't exist, and ``-l`` says that the users to hydrate are given
in the form of Twitter lists. (If you'd left the header line out of the CSV
file and wanted to avoid using xargs, note that you could instead write
something like ``twclient fetch users -v -b -l $(cat lists.csv)``.)

Similarly, you can hydrate the individual users as follows:

.. code-block:: bash

   tail -n +2 users.csv | xargs twclient fetch users -v -b -n

A noteworthy difference from the case of lists is that you use the ``-n``
option, for users identified by screen names, rather than the ``-l`` option for
lists.

Tagging users
---------------

Having fetched the users, we may want to give them *tags* for easier reference
in SQL or later commands. Twclient has a tag table that allows you to associate
arbitrary tag names with user IDs, to keep track of relevant groups of users in
your analysis. Let's say we want to track all individually fetched users
together, and all users retrieved from lists together, as two groups.

First, we need to create a tag:

.. code-block:: bash

   twclient tag create twitter_lists

Next, we associate the new tag with the users it should apply to:

.. code-block:: bash

   tail -n +2 lists.csv | xargs twclient tag apply twitter_lists -l

Similarly, we can tag the individually fetched users:

.. code-block:: bash

   twclient tag create twitter_users
   tail -n +2 users.csv | xargs twclient tag apply twitter_users -l

Users fetched from Twitter lists will be associated with the lists they are
members of in the ``list`` and ``user_list`` tables, so there's no need to tag
lists individually.

Finally, we might want to create one tag referring to both sets of users (for
example, to run a regular job for fetching everyone's tweets). We do the same
two-step as above:

.. code-block:: bash

   twclient tag create universe
   twclient tag apply universe -g twitter_users twitter_lists

This time, however, you can see that the ``-g`` option allows selecting users
to operate on---whether that's tagging, hydrating, or fetching tweets and
follow edges---according to tags you've defined.

Fetching tweets
-----------------

Now, with fully hydrated users, it's time to get down to one of our primary
jobs: fetching the users' tweets. We can do this with the ``twclient fetch
tweets`` command:

.. code-block:: bash

   twclient fetch tweets -v -b -g universe

As before, ``-v`` asks for verbose output, ``-b`` says to ignore nonexistent or
protected users rather than aborting the job, and ``-g universe`` says to fetch
tweets for those users tagged ``universe``.

Note that twclient also extensively normalizes the tweet objects returned by
Twitter. In addition to the tweet text, we pull out urls, hashtags, "cashtags",
user mentions and other things so that it's easy to compute derived datasets
like the mention / quote / etc graphs over users. (For how to do this and
sample SQL, see the vignette on :doc:`exporting data </vignettes/export>`.) The
raw json API responses are also saved so that you can work with data we don't
parse.

Fetching the follow graph
---------------------------

Finally, we want to get the user IDs of our target users' followers and
friends. (A "friend" is Twitter's term for the opposite of a follower: if A
follows B, B is A's friend and A is B's follower.) There are two more
``twclient fetch`` subcommands for this: ``twclient fetch friends`` and
``twclient fetch followers``. Neither command hydrates users, because the
underlying Twitter API endpoints don't, so the ``follow`` table will end up
being populated with bare numeric user IDs.

Here's fetching friends, using options you've seen all of by now:

.. code-block:: bash

   twclient fetch friends -v -b -g universe

And here's followers:

.. code-block:: bash

   twclient fetch followers -v -b -p -j 5000 -g universe

The one new flag used here, ``-j 5000``, indicates the size of the batch used
for loading follow edges. The default if you don't use ``-j`` is to accumulate
all edges in memory and load them at once, which is faster but can cause
out-of-memory errors for large accounts. Specifying ``-j`` will trade runtime
for memory and let you process these large accounts.

The ``-v`` flag is also particularly useful here: if you're working with users
who have many followers or friends, it can take some time to process them.
Verbose output will print progress information (``-v -v`` will print even more)
to help monitor the job.

The fetched follow graph data itself is stored in a `type-2 SCD
<https://en.wikipedia.org/wiki/Slowly_changing_dimension#Type_2:_add_new_row>`__
format, which (without getting into the details) means that you can just keep
running these commands and storing multiple snapshots at different times,
without using enormous amounts of disk space. (See the :doc:`exporting data
vignette </vignettes/export>` for details of how to get follow graph snapshots
out of the SCD table.)

---------------------------
  Putting it all together
---------------------------

Here's all of our hard work in one little script (again, remember that the user
IDs and list IDs are fake for privacy; replace them with real ones if
you want to run this example):

.. code-block:: bash

   #!/bin/bash

   set -xe

   # We assume you've already installed the twclient package (e.g., from PyPI)
   # and gotten API keys, so we won't show any of that here. See also the
   # command-line -h/--help option for more info.

    cat << EOF > users.csv
    screen_name
    user1
    user2
    user3
    test1234
    foobar
    stuff
    EOF

    cat << EOF > lists.csv
    list
    cspan/members-of-congress
    2389231097
    18230127
    nytimes/nyt-journalists
    20218236
    1937309
    1824379139
    EOF

   twclient config add-db -f /path/to/your/project/sqlite.db db
   twclient initialize -y

   twclient config add-api -n twitter1 \
       --consumer-key XXXXX \
       --consumer-secret XXXXXX \
       --token XXXXXX \
       --token-secret XXXXXX

   twclient config add-api -n twitter2 \
       --consumer-key XXXXX \
       --consumer-secret XXXXXX \
       --token XXXXXX \
       --token-secret XXXXXX

   tail -n +2 lists.csv | xargs twclient fetch users -v -b -l

   twclient tag create twitter_lists
   tail -n +2 lists.csv | xargs twclient tag apply twitter_lists -l

   tail -n +2 users.csv | xargs twclient fetch users -v -b -n

   twclient tag create twitter_users
   tail -n +2 users.csv | xargs twclient tag apply twitter_users -l

   twclient tag create universe
   twclient tag apply universe -g twitter_users twitter_lists

   twclient fetch tweets -v -b -g universe

   twclient fetch friends -v -b -g universe
   twclient fetch followers -v -b -j 5000 -g universe

Tada! Now you have data in a DB. You can use canned SQL queries, like those in
the :doc:`exporting data vignette </vignettes/export>`, to get whatever piece
of data you want out of it: the follow graph, a user's tweets, mention / quote
/ reply / retweet graphs, etc. Your creativity in SQL is the limit.

Wasn't that easier than you're used to?
