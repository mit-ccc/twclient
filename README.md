[![License](https://img.shields.io/:license-mit-blue.svg?style=flat)](https://mit-license.org/)

# twclient

This package provides a high-level command-line client for the Twitter API, with
a focus on loading data into a database. The goal is to be higher-level than
twurl and offer useful primitives for researchers who want to get data out of
Twitter, without worrying about the details. The client can handle multiple sets
of API credentials seamlessly, helping avoid rate limit issues.

An example of usage:
```
#
# Setup
#

# Set up the database. This creates a persistent profile in a config file, no
# need to type the URL repeatedly.
twitter config add-db -u "postgresql:///" postgres

# Set up the Twitter credentials. Similarly, this stores the credentials in a
# config file for ease of use. Only two sets of credentials are shown, but
# arbitrarily many can be added.
twitter config add-api -n twitter1 \
    --consumer-key XXXXX \
    --consumer-secret XXXXXX \
    --token XXXXXX \
    --token-secret XXXXXX

twitter config add-api -n twitter2 \
    --consumer-key XXXXX \
    --consumer-secret XXXXXX \
    --token XXXXXX \
    --token-secret XXXXXX

# Initialize the DB schema, dropping any existing data.
twitter initialize -y

#
# Pull data
#

# Load some users and their basic info
twitter fetch users -n wwbrannon socialmachines mit -l mit/a-twitter-list

# Tag them for ease of analysis
twitter tag create subjects
twitter tag apply subjects -n wwbrannon socialmachines mit -l mit/a-twitter-list

# Get their friends and followers
twitter fetch friends -g subjects
twitter fetch followers -g subjects

# Get their tweets
twitter fetch tweets -g subjects
```

After all of this, the loaded data is in the database configured with `config
add-db`. You can query it with the usual tools, and useful features have been
normalized out to save processing time. The raw API responses are also saved for
later analysis.

