# twclient

FIXME update this and add badges

This package provides a high-level command-line client for the Twitter API, with a focus on loading data into a database. The goal is to be higher-level than twurl and offer useful primitives for researchers who want to get data out of Twitter, without worrying about the details. The client can handle multiple sets of API credentials seamlessly, helping avoid rate limit issues.

An example of usage:
```
# set up the DB and the Twitter credentials
twitter add-db -s /var/run/postgresql # only local socket auth supported so far
twitter add-api -n twitter1 --consumer-key XXXXX --consumer-secret XXXXXX
twitter add-api -n twitter2 --consumer-key XXXXX --consumer-secret XXXXXX
twitter add-api -n twitter3 --consumer-key XXXXX --consumer-secret XXXXXX

# initialize the DB schema
twitter initialize -y

# load some users, tagging them "subjects" for later use
twitter user_info -n wwbrannon socialmachines mit -u 'subjects'

# get their friends and followers, tagging them as well:
twitter friends -g subjects -u subjects-friends
twitter followers -g subjects -u subjects-followers

# get their tweets:
twitter tweets -g subjects

# the friends and followers are just bare IDs, but if you want to "hydrate" them:
twitter user_info -g subjects-friends
twitter user_info -g subjects-followers
```

After all of this, the loaded data is in the database configured with `add-db`. You can query it with the usual tools, and useful features have been normalized out to save processing time. The raw API responses are also saved for later analysis.

