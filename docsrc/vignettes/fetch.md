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

Note that Twitter has other data sources than the REST API, in particular the
[PowerTrack](https://developer.twitter.com/en/docs/twitter-api/enterprise/historical-powertrack-api/overview)
API, and this package does not support those.

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

If you want to use one of these which DB should you choose? If, like me, you're
on a Mac, [Postgres.app](https://postgresapp.com/) is an excellent and
user-friendly choice. SQLite has the advantage of being built into Python, but
you may want to install a command-line shell via a package manager like
[Homebrew](https://brew.sh/) (on a Mac) or apt-get (on Debian-based Linux). You
can also download it from the [SQLite
website](https://www.sqlite.org/index.html). Other DBMSs, like MySQL or Oracle,
should also work but have not been tested extensively.

We'll use Postgres for the rest of this vignette.

Having set up our database system, we need to do two more things to make it
usable: tell twclient how to use it, and install the data model. First, we'll
use a `twitter config` subcommand to set up the database:

```
twitter config add-db -u "postgresql:///" postgres
```

This command tells twclient to create a persistent profile for a database and
call it "postgres", with the database itself identified by a [sqlalchemy
connection URL](https://docs.sqlalchemy.org/en/14/core/engines.html#database-urls).
The specific URL we have here, `postgresql:///`, indicates the default database
on a Postgres DBMS accessed through the default local Unix socket, with
trust/passwordless authentication, using sqlalchemy's default Postgres driver.
(If, like me, you're using Postgres.app on a Mac, this is likely the URL you
want to use.) The database profile is stored in a twclient configuration file,
by default `~/.twclientrc`, so that you won't need to continually provide the
database URL for each command.

Next up, we have to install the data model: create the tables, columns, keys and
other DB objects the twclient package uses. Be aware that doing this will **drop
all existing twclient data in your database**. The `twitter initialize` command
will do the trick, but to confirm that you understand running it will **drop all
existing twclient data in your database** you have to specify the `-y` flag:

```
twitter initialize -y
```

And that's it! If you fire up a database client (psql in the case of this
example), you'll see a new database schema installed. The tables, columns and
other objects are documented, in the form of their sqlalchemy model classes, in
the API documentation for twclient.models.

API setup
---------
You can't get data from the Twitter API without API credentials, so the next
step is to get at least one set of credentials. If you don't already have
credentials, Twitter has
[documentation](https://developer.twitter.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api)
on how to get them.

You'll generally receive four pieces of
[OAuth](https://en.wikipedia.org/wiki/OAuth) authentication information: a
consumer key, consumer secret, access token and access token secret. If using
[OAuth 2.0 bearer tokens](https://oauth.net/2/bearer-tokens/) you may receive
only a consumer key and consumer secret. Regardless, you can add them to
twclient as follows (replacing the "XXXXX" with your values, and omitting token
and token secret if using a bearer token):

```
twitter config add-api -n twitter1 \
    --consumer-key XXXXX \
    --consumer-secret XXXXX \
    --token XXXXX \
    --token-secret XXXXX
```

Similarly to the database setup, this command stores the credentials in your
config file under an API profile named "twitter1" for ease of use. We've only
added one set of credentials here, but you can add arbitrarily many under
different names. Twclient will seamlessly switch between them as each one hits
rate limits.

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

### A word about identifiers
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
but not one file which mixes user IDs and screen names together. This is because
of the way the underlying Twitter API endpoints are implemented: They'll accept
mixed references to lists, but not to users.

### Hydrating users
The first step is to
[hydrate](https://stackoverflow.com/questions/34191022/what-does-hydrate-mean-on-twitter/34192633)
the target users, which confirms with the Twitter API that they exist, retrieves
some summary information about them and creates records for them in the
database. You can do this with the `twitter fetch` family of commands, and
specifically `twitter fetch users`. We'll start by fetching the users in the
lists of `lists.csv`, though you could do the individual users first:

```
tail -n +2 lists.csv | xargs twitter -v fetch users -b -l
```

This command skips the CSV header line (via `tail -n +2 lists.csv`), which
twclient doesn't actually use, and pipes the rest of it to `twitter -v fetch
users -b -l` via `xargs`. The `-v` flag requests verbose output, `-b` says to
continue even if the Twitter API says some of the lists requested are protected
or don't exist, and `-l` says that the users to hydrate are given in the form of
Twitter lists. (If you'd left the header line out of the CSV file and wanted to
avoid using xargs, note that you could instead write something like `twitter -v
fetch users -b -l $(cat lists.csv)`.)

Similarly, you can hydrate the individual users as follows:

```
tail -n +2 users.csv | xargs twitter -v fetch users -b -n
```

A noteworthy difference from the case of lists is that you use the `-n` option,
for users identified by screen names, rather than the `-l` option for lists.

### Tagging users
Having fetched the users, we may want to give them _tags_ for easier reference
in SQL or later commands. Twclient has a tag table that allows you to associate
arbitrary tag names with user IDs, to keep track of relevant groups of users in
your analysis. Let's say we want to track all individually fetched users
together, and all users retrieved from lists together, as two groups.

First, we need to create a tag:
```
twitter tag create twitter_lists
```

Next, we associate the new tag with the users it should apply to:
```
tail -n +2 lists.csv | xargs twitter tag apply twitter_lists -l
```

Similarly, we can tag the individually fetched users:
```
twitter tag create twitter_users
tail -n +2 users.csv | xargs twitter tag apply twitter_users -l
```

Users fetched from Twitter lists will be associated with the lists they are
members of in the `list` and `user_list` tables, so there's no need to tag
lists individually.

Finally, we might want to create one tag referring to both sets of users (for
example, to run a regular job for fetching everyone's tweets). We do the same
two-step as above:
```
twitter tag create universe
twitter tag apply universe -g twitter_users twitter_lists
```

This time, however, you can see that the `-g` option allows selecting users to
operate on---whether that's tagging, hydrating, or fetching tweets and follow
edges---according to tags you've defined.

### Fetching tweets
Now, with fully hydrated users, it's time to get down to one of our primary
jobs: fetching the users' tweets. We can do this with the `twitter fetch tweets`
command:

```
twitter -v fetch tweets -b -g universe
```

As before, `-v` asks for verbose output, `-b` says to ignore nonexistent or
protected users rather than aborting the job, and `-g universe` says to fetch
tweets for those users tagged `universe`.

Note that twclient also extensively normalizes the tweet objects returned by
Twitter. In addition to the tweet text, we pull out urls, hashtags, "cashtags",
user mentions and other things so that it's easy to compute derived datasets
like the mention / quote / etc graphs over users. (For how to do this and sample
SQL, see the extracting data vignette.) The raw json API responses are also
saved so that you can work with data we don't parse.

### Fetching the follow graph
Finally, we want to get the user IDs of our target users' followers and friends.
(A "friend" is Twitter's term for the opposite of a follower: if A follows B, B
is A's friend and A is B's follower.) There are two more `twitter fetch`
subcommands for this: `twitter fetch friends` and `twitter fetch followers`.
Neither command hydrates users, because the underlying Twitter API endpoints
don't, so the `follow` table will end up being populated with bare numeric user
IDs.

Here's fetching friends, using options you've seen all of by now:
```
twitter -v fetch friends -b -g universe
```

And here's followers:
```
twitter -v fetch followers -b -p -j 5000 -g universe
```

The one new flag used here, `-j 5000`, indicates the size of the batch used for
loading follow edges. The default if you don't use `-j` is to accumulate all
edges in memory and load them at once, which is faster but can cause
out-of-memory errors for large accounts. Specifying `-j` will trade runtime for
memory and let you process these large accounts.

The `-v` flag is also particularly useful here: if you're working with users who
have many followers or friends, it can take some time to process them. Verbose
output will print progress information (`-v -v` will print even more) to help
monitor the job.

The fetched follow graph data itself is stored in a [type-2
SCD](https://en.wikipedia.org/wiki/Slowly_changing_dimension#Type_2:_add_new_row)
format, which (without getting into the details) means that you can just keep
running these commands and storing multiple snapshots at different times,
without using enormous amounts of disk space. (See the extracting data vignette
for details of how to get follow graph snapshots out of the SCD table.)

Putting it all together
-----------------------
Here's all of our hard work in one little script:

```
#!/bin/bash

set -xe

# We assume you've already installed the twclient package (e.g., from PyPI), set
# up the database, and gotten API keys, so we won't show any of that here. See
# also the command-line -h/--help option for more info.

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

twitter -v fetch tweets -b -g universe

twitter -v fetch friends -b -g universe
twitter -v fetch followers -b -j 5000 -g universe
```

Tada! Now you have data in a DB. You can use canned SQL queries, like those
in the extracting data vignette, to get whatever piece of data you want out of
it: the follow graph, a user's tweets, mention / quote / reply / retweet graphs,
etc. Your creativity in SQL is the limit.

Wasn't that easier than you're used to?

