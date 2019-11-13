# twclient
A high-level command-line client for the Twitter API

This package provides a high-level command-line client for the Twitter API, with a focus on loading data into a Postgres instance. The goal is to be higher-level than twurl and offer useful primitives for researchers who want to get data out of Twitter, without worrying about the details. The client can handle multiple sets of API credentials seamlessly, helping avoid rate limit issues.

An example of usage (API credentials are pulled from `~/.twurlrc`):
```
# set up the database schema:
twitter -d PostgresDSN initialize -y

# load some users, tagging them "subjects" for later use
twitter -d PostgresDSN user_info -n wwbrannon socialmachines mit -u 'subjects'

# get their friends and followers, tagging them as well:
twitter -d PostgresDSN friends -g subjects -u subjects-friends
twitter -d PostgresDSN followers -g subjects -u subjects-followers

# get their tweets:
twitter -d PostgresDSN tweets -g subjects

# the friends and followers are just bare IDs, but if you want to "hydrate" them:
twitter -d PostgresDSN user_info -g subjects-friends
twitter -d PostgresDSN user_info -g subjects-followers
```

After all of this, the loaded data is in the Postgres DB specified by the DSN provided to `-d`. You can query it with `psql` or other tools, and useful features have been normalized out to save processing time. The raw API responses are also saved for later analysis.

Future development might focus on two current shortcomings:
* It's not multithreaded, which can fail to take advantage of high rate limits.
* The Postgres backend is hardcoded, ugly, and should be replaced with a more generic layer like sqlalchemy for extensibility.

