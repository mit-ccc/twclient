.. |MIT license| image:: https://img.shields.io/badge/License-MIT-blue.svg
   :target: https://mit-license.org/
.. |License| image:: https://img.shields.io/:license-mit-blue.svg?style=flat
   :target: https://mit-license.org/

twclient
========

This package provides a high-level command-line client for the Twitter API,
with a focus on loading data into a database. The goal is to be higher-level
than twurl or tweepy and offer useful primitives for researchers who want to
get data out of Twitter, without worrying about the details. The client can
handle multiple sets of API credentials seamlessly, helping avoid rate limit
issues. There's also support for exporting bulk datasets from the fetched raw
data.

~~~~~~~~~
  Setup
~~~~~~~~~

Install the package from pypi, or by cloning this repo and using ``pip
install`` if you want to use the development version. After that, you need to
tell twclient about your database backend and Twitter credentials:

.. code-block:: bash

   # Set up the database. This creates a persistent profile in a config file, no
   # need to type the URL repeatedly. You specify a database via a sqlalchemy
   # connection url, which can be sqlite (as here) for a zero-configuration
   # setup, and can also be something like "postgresql:///" to use a
   # traditional full-fledged database you've set up separately.
   twclient config add-db -u "sqlite:///home/user/twitter.db" sqlite

   # Set up the Twitter credentials. As with the database setup, this stores
   # the credentials in a config file for ease of use. Only two sets of
   # credentials are shown, but arbitrarily many can be added.
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

   # Initialize or re-initialize the DB schema, **dropping any existing data**.
   twclient initialize -y

~~~~~~~~~~~~~~~~
  Pulling data
~~~~~~~~~~~~~~~~

To actually pull data, use the ``twclient fetch`` command. The ``twclient tag``
command can help keep track of users and datasets. We'll pull information about
two specific users and a Twitter list here:

.. code-block:: bash

   # Load some users and their basic info
   twclient fetch users -n wwbrannon socialmachines mit -l mit/a-twitter-list

   # Tag them for ease of analysis
   twclient tag create subjects
   twclient tag apply subjects -n wwbrannon socialmachines mit -l mit/a-twitter-list

   # Get their friends and followers
   twclient fetch friends -g subjects
   twclient fetch followers -g subjects

   # Get their tweets
   twclient fetch tweets -g subjects

At this point, the loaded data is in the database configured with ``config
add-db``. Useful features have been normalized out to save processing time. The
raw API responses are also saved for later analysis.

~~~~~~~~~~~~~~~~~~
  Exporting data
~~~~~~~~~~~~~~~~~~

You can query the data with the usual database tools (``psql`` for postgres,
``sqlite3`` for sqlite, ODBC clients, etc.) or export certain pre-defined bulk
datasets with the ``twclient export`` command. For example, here's getting the
follow graph and mention graph:

.. code-block:: bash

    twclient export follow-graph -o follow-graph.csv
    twclient export mention-graph -o mention-graph.csv

If you want to restrict the export to only the users specified above:

.. code-block:: bash

    twclient export follow-graph -g subjects -o follow-graph.csv
    twclient export mention-graph -g subjects -o mention-graph.csv

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  Feedback or Contributions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you come across a bug, please report it on the Github issue tracker. If you
want to contribute, reach out! Extensions and improvements are welcome.
