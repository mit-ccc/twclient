#!/bin/bash

set -xe

#
# Fetch user info and tag users
#

# need to get user info first so there are user records to specify for
# tweet/follower/friend fetching

## Lists first
# they don't have to be first, just arbitrarily

# the lists can be either the user/slug-name format or the numeric list ID and
# you can mix them together in the arguments to "twitter fetch users -l"
tail -n +2 lists.csv | xargs twitter -v fetch users -b -l

twitter tag create twitter_lists
tail -n +2 lists.csv | xargs twitter tag apply twitter_lists -l

## Then users

# unlike with lists, there isn't a command-line option that takes both user IDs
# and screen names at once (because they ultimately have to be separate Twitter
# API calls) so you can't mix IDs and screen names in the users.csv file
tail -n +2 users.csv | xargs twitter -v fetch users -b -n

twitter tag create twitter_users
tail -n +2 users.csv | xargs twitter tag apply twitter_users -l

## Tag them all together for easy fetching
twitter tag create universe
twitter tag apply universe -g users lists

#
# Fetch tweets and follow graph data
#

twitter -v fetch tweets -b -p -g universe

# if you have really large accounts like @barackobama these can be very very
# slow and the "-v" option (for "verbose") will print ongoing progress info
twitter -v fetch friends -b -p -g universe
twitter -v fetch followers -b -p -j 5000 -g universe

# Tada! Now you have data in a DB, you can (e.g.) use the queries in ../sql/
# to get things like the follow/mention graphs out of it.

