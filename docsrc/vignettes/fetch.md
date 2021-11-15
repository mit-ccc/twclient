Extracting data
===============
FIXME link the other rst files after conversion

So you want to analyze some Twitter data. (That's why you're here, right?) This
vignette walks through how to get set up and how to acquire the data.

**Obligatory disclaimer / reminder**: You should comply with Twitter's terms of
service and respect user privacy. It's important to only access data you have a
right to access.

Twclient makes acquiring data easier than directly interacting with the Twitter
REST API, which you can do through a lightweight client like Twitter's own
[twurl](https://github.com/twitter/twurl) or a more featureful package like
[tweepy](https://www.tweepy.org/). Using either of these makes you do quite a
bit of work you'd rather avoid: thinking about cursoring and pagination of
results, manually handling multiple sets of credentials if you have more than
one, and of course munging data into the format you want.

Data munging in particular is not a simple task. You may have to keep and
organize the raw json responses from Twitter's API, and then extract things from
them via a tool like [jq](https://stedolan.github.io/jq/); if using tweepy, you
have to write some python code to serialize the User, Tweet, etc, objects it
produces to a format you can work with.

In general, of course, there's no way around this: if you want to write an
application like a Twitter client, which people can use to view their feeds,
post tweets, and whatever else, you need the API in its full complexity. But
here we have a simpler task---read-only scraping of data---and so we can make a
simpler tool. (For formatting it and extracting it from the database, see the
other vignette on extracting data.)

FIXME refer to other Twitter data sources this doesn't support

Enough talk! How do you get started?

Database setup
--------------
The first step is to set up a database backend. You can use any DB that
[sqlalchemy supports](https://docs.sqlalchemy.org/en/14/dialects/), which with
plugins is quite a few to choose from. This is less intimidating than it may
sound---in fact it's positively easy. Two good choices are
[Postgres](https://www.postgresql.org/), which we've used for the SQL examples
in the extraction vignette, and the extremely lightweight
[SQLite](https://www.sqlite.org/index.html).

Which DB should you choose? If, like me, you're on a Mac,
[Postgres.app](https://postgresapp.com/) 

SQLite, on the other hand,

API setup
---------
get Twitter API credentials. 

Actually pulling data
---------------------
Now comes the fun part: actually downloading some data. We'll assume you've
pulled together sets of Twitter users and [Twitter
lists](https://help.twitter.com/en/using-twitter/twitter-lists) you want to
retrieve information on. This example will use the following two files, one each
of individual users and lists of users.

Here's `users.csv`:
```
screen_name
user1
user2
user3
test1234
foobar
stuff
```

And here's `lists.csv`:
```list
cspan/members-of-congress
23965249864
182359253
nytimes/nyt-journalists
14624234
185239864
172409353
```

---
A word about identifiers:

In general, Twitter allows you to refer to a user or
list by either a) a numeric user ID or list ID, or b) a human-readable name.
Readable names for users are called screen names, and for lists are called "full
names." List full names consist of the screen name of the user who owns the
list and a list-specific slug, separated by a slash. (For example,
"cspan/members-of-congress".)

With twclient, you can mix numeric and human-readable names for lists, as in
`lists.csv` above, but not for users. That is, you could instead use this
`users_alternative.csv`:
```
user_id
39702507914
28723520928
1825471204
1853209475
4382530952834
1725438692309
```
but not one which mixes user IDs and screen names together. This is because of
the way the underlying Twitter API endpoints are implemented: They'll accept
mixed references to lists, but not to users.

---

FIXME this shouldn't appear as a script twice, you should just have these #
comments as inline text

```
# Set up the database. This creates a persistent profile in a config file called
# `~/.twclientrc`, so there's no need to type the URL repeatedly.
twitter config add-db -u "postgresql:///" postgres

# Initialize the DB schema, **dropping any existing data**.
twitter initialize -y

# Set up the Twitter credentials. Similarly, this stores the credentials in a
# config file for ease of use. Only two sets of credentials are shown, but
# arbitrarily many can be added. If you're using bearer tokens, leave off the
# token and token secret.
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

#
# Fetch user info and tag users
#

# We need to get user info first so there are user records to specify for
# tweet/follower/friend fetching. First, let's do the lists. (Note that they
# don't in general have to be first, we've just arbitrarily decided to do them
# in this order.) The lists can be either the user/slug-name format or the
# numeric list ID, and you can mix them together in the arguments to `twitter
# fetch users -l`.

# NB: twclient doesn't actually use the CSV header line, so you have to either
# leave it out to begin with or remove it, which is what `tail -n +2` is for.
# You could instead write, e.g., `twitter -v fetch users -b -l $(cat lists.csv)`
# if you've left out the header line and don't want to use xargs.
tail -n +2 lists.csv | xargs twitter -v fetch users -b -l

# Tag the users for easier reference in SQL. (Assuming there's some reason we'd
# want to refer to all users who came from any Twitter list as a group.) Users
# will be associated with the lists they were fetched from in the `list` and
# `user_list` tables, so there's no need to tag the lists individually.
twitter tag create twitter_lists  # first, make the tag
tail -n +2 lists.csv | xargs twitter tag apply twitter_lists -l  # apply the tag

# Next, we need to fetch the list of individual users. Unlike with lists, there
# isn't a command-line option that takes both user IDs and screen names at once
# (because they ultimately have to be separate Twitter API calls) so you can't
# mix IDs and screen names in the users.csv file.

tail -n +2 users.csv | xargs twitter -v fetch users -b -n

# Once again, tag the users to simplify working with them in SQL.
twitter tag create twitter_users
tail -n +2 users.csv | xargs twitter tag apply twitter_users -l

# To illustrate the many ways you can refer to a group of users to do something
# to: create one tag that applies to both the list-sourced users and individual
# users fetched above. The "-g" option says "all users with these tags."
twitter tag create universe
twitter tag apply universe -g twitter_users twitter_lists

#
# Fetch other data: follow graph, tweets, data derived from tweets
#

# What the options here mean (see the command line -h/--help option for the
# canonical reference):
# o) `-v`: If you have many accounts, or very large accounts like @barackobama,
#    these operations can be slow, so the `-v` option (for "verbose") will print
#    ongoing progress information.
# o) `-b`: 
# o) `-p`: 
# o) `-j 5000`: 
# o) `-g universe`: 

# The fetched follow graph data is stored in a type-2 SCD format, which is a
# fancy way of saying you can just keep running this and storing multiple
# snapshots at different times without using enormous amounts of disk space.
twitter -v fetch friends -b -p -g universe
twitter -v fetch followers -b -p -j 5000 -g universe

# Note that this also extensively normalizes the tweets. We pull out urls,
# hashtags, "cashtags", user mentions and other things so that it's easy to get
# derived datasets like the mention / quote / etc graphs over users.
twitter -v fetch tweets -b -p -g universe
```

Putting it all together
-----------------------
Here's all of our hard work in one little script:

```
#!/bin/bash

set -xe

# We assume you've already installed the package (e.g., from PyPI) so we won't
# do that here. See also the command-line -h/--help option for more info.

twitter config add-db -u "postgresql:///" postgres
twitter initialize -y

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

tail -n +2 lists.csv | xargs twitter -v fetch users -b -l

twitter tag create twitter_lists  # first, make the tag
tail -n +2 lists.csv | xargs twitter tag apply twitter_lists -l  # apply the tag

tail -n +2 users.csv | xargs twitter -v fetch users -b -n

twitter tag create twitter_users
tail -n +2 users.csv | xargs twitter tag apply twitter_users -l

twitter tag create universe
twitter tag apply universe -g twitter_users twitter_lists

twitter -v fetch friends -b -p -g universe
twitter -v fetch followers -b -p -j 5000 -g universe

twitter -v fetch tweets -b -p -g universe
```

Tada! Now you have data in a DB. You can use canned SQL queries, like those
in the extracting data vignette, to get whatever piece of data you want out of
it: the follow graph, a user's tweets, mention / quote / reply / retweet graphs,
etc. Your creativity in SQL is the limit.

Wasn't that easier than you're used to?

