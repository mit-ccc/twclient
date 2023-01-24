.. image:: https://img.shields.io/badge/License-Apache_2.0-blue.svg
   :target: https://www.apache.org/licenses/LICENSE-2.0
   :alt: Apache 2.0 License

.. image:: https://badge.fury.io/py/twclient.svg
   :target: https://pypi.python.org/pypi/twclient/
   :alt: PyPi version

.. image:: https://img.shields.io/pypi/pyversions/twclient.svg
   :target: https://pypi.python.org/pypi/twclient/
   :alt: Python versions

..
    .. image:: https://readthedocs.org/projects/twclient/badge/?version=latest
       :target: http://twclient.readthedocs.io/?badge=latest
       :alt: Documentation Status

twclient
========

This package provides a high-level command-line client for the Twitter API,
with a focus on loading data into a database for analysis or bulk use.

Why use this project?
=====================

This project offers high-level primitives for researchers who want to get
data out of Twitter, without worrying about the API details. The client can
handle multiple sets of API credentials seamlessly, helping avoid rate limit
issues. [1]_ There's also support for exporting bulk datasets from the fetched
raw data.

Installation
============

Install the package from pypi:

.. code-block:: bash

   pip3 install twclient

or, if you want to use the development version, clone this repo and install in
editable mode:

.. code-block:: bash

   git clone git@github.com:mit-ccc/twclient.git && cd twclient
   pip3 install -e .

or use ``pip3 install -e .[dev]`` to also install all dev dependencies.

Usage
=====

First, you need to tell twclient about your database backend and Twitter
credentials. On the database side, we've only tested with Postgres and SQLite.
While the package may well work with other DB engines, be aware that you may
encounter issues.

Setup: Database
---------------

The database backend can be either sqlite or an arbitrary database
specified by a sqlalchemy connection string.

You can set up the database in one of two ways. Both create a persistent
profile in your ``.twclientrc`` file (or whatever other file you specify), so
there's no need to type the database details repeatedly.

First, you can specify the DB with a sqlalchemy connection URL:

.. code-block:: bash

   # Postgres -- this becomes the default DB because you've created it first
   twclient config add-db -u "postgresql+psycopg2://username@hostname:5432/dbname" my_postgres_db

   # Or you could use SQLite
   twclient config add-db -u "sqlite:///home/user/twitter.db" my_sqlite_db

There's also support for using SQLite without having to think about sqlalchemy
and connection URLs:

.. code-block:: bash

   twclient config add-db -f ./twitter2.db my_sqlite_db2

If you specify a file-backed sqlite DB, as in the examples above, it'll be
created if it doesn't exist. Other databases (Postgres, for example) will need
to be set up separately.

Finally, you have to install our database schema into your database to receive
Twitter data:

.. code-block:: bash

   # You have to specify the -y to say you're aware all data will be dropped
   twclient initialize -d my_postgres_db -y

Be aware that doing this will **DROP ALL EXISTING TWCLIENT DATA**!!! (Or other
tables with the same names.) If you're not just getting started, check to make
sure you're using a new or empty database, don't care about the contents,
and/or have backups before running this.

Setup: Twitter
----------------

You'll also need to set up your Twitter API credentials. [1]_ As with the
database setup, doing this stores the credentials in a config file (the same
config file as for database info) for ease of use. Only two sets of credentials
are shown, but you can add as many as you want.

Here's an example of adding two API keys:

.. code-block:: bash

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

Here's an example of adding credentials that use `app-only auth <https://developer.twitter.com/en/docs/authentication/oauth-2-0/application-only>`_:

.. code-block:: bash

   twclient config add-api -n twitter3 \
       --consumer-key XXXXX \
       --consumer-secret XXXXXX

Pulling data
--------------

To actually pull data, use the ``twclient fetch`` command. We'll pull
information about three specific users and a Twitter list here. Note that you
can refer to lists either by their "slug" (username/listname) or by the ID at
the end of a URL of the form `https://twitter.com/i/lists/53603015`.

First, let's load some users and their basic info:

.. code-block:: bash

   # you could instead also end this with "-l 53603015"; it's the same list
   twclient fetch users -n wwbrannon CCCatMIT MIT -l MIT/peers1

Now, to save typing, let's use the ``twclient tag`` command to apply a tag we
can use to keep track of these users later:

.. code-block:: bash

   twclient tag create subjects
   twclient tag apply subjects -n wwbrannon CCCatMIT MIT -l MIT/peers1

We can now use this tag in specifying users, such as which users we'd like to
fetch tweets for:

.. code-block:: bash

   twclient fetch tweets -g subjects

And if we also want their follow-graph info (note that a "friend" is Twitter's
term for a follow-ee, an account you follow):

.. code-block:: bash

   twclient fetch friends -g subjects
   twclient fetch followers -g subjects

At this point, the loaded data is in the database configured with ``config
add-db``. Useful features have been normalized out to save processing time. The
raw API responses are also saved for later analysis.

Exporting data
----------------

You can query the data with the usual database tools (``psql`` for postgres,
``sqlite3`` for sqlite, ODBC clients, etc.) or export certain pre-defined bulk
datasets with the ``twclient export`` command. For example, here are the follow
graph and mention graph over users:

.. code-block:: bash

    twclient export follow-graph -o follow-graph.csv
    twclient export mention-graph -o mention-graph.csv

If you want to restrict the export to only the users specified above:

.. code-block:: bash

    twclient export follow-graph -g subjects -o follow-graph.csv
    twclient export mention-graph -g subjects -o mention-graph.csv

For other exports and other options, see the documentation.

Feedback or Contributions
=========================

If you come across a bug, please report it on the Github issue tracker. If you
want to contribute, reach out! Extensions and improvements are welcome.

Copyright
===========

Copyright © 2019-2023 Massachusetts Institute of Technology.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this software except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

.. [1] Of course, you'll need to make sure you have the right to use all of
   your credentials and are complying with Twitter's terms of use.
