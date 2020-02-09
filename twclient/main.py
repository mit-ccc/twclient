#!/usr/bin/env python3

##
## The command-line interface script
##

import json
import logging
import argparse

import twclient.utils as ut

from twclient.job import StatsJob, InitializeJob, UserInfoJob, FollowJob, TweetsJob

logger = logging.getLogger(__name__)

def main():
    ##
    ## Parse arguments
    ##

    desc = 'Fetch Twitter data and load into Postgres'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-v', '--verbose', action='count',
                        help='verbosity level (repeat for more)')

    # Database connection options
    dbgrp = parser.add_mutually_exclusive_group()
    dbgrp.add_argument('-s', '--socket', default='/var/run/postgresql/',
                       help='directory containing Unix socket')
    dbgrp.add_argument('-d', '--dsn',
                       help='database DSN (default local Unix socket)')

    # Twitter authentication options
    parser.add_argument('-p', '--twurlrc', default='~/.twurlrc',
                        help='location of twurlrc file (default ~/.twurlrc')

    def common_arguments(sp):
        sp.add_argument('-u', '--user-tag',
                        help='tag to apply to any loaded / updated users')
        sp.add_argument('-b', '--abort-on-bad-targets', action='store_true',
                        help="abort if a requested user doesn't exist")
        sp.add_argument('-e', '--transaction', action='store_true',
                        help='load in one transaction')
        sp.add_argument('-z', '--load-batch-size',
                        help='run loads to DB in batches of this size')

        grp = sp.add_mutually_exclusive_group(required=True)
        grp.add_argument('-s', '--user-spec',
                         choices=['all', 'missing'],
                         help='Canned user specification')
        grp.add_argument('-g', '--select-tag',
                         help='process only users with this tag')
        grp.add_argument('-i', '--user-ids', nargs='+',
                        help='get info for the given list of twitter user IDs')
        grp.add_argument('-n', '--screen-names', nargs='+',
                        help='get info for given list of twitter screen names')

        return sp, grp

    sp = parser.add_subparsers(dest='command')
    sp.required = True

    inp = sp.add_parser('initialize', help='Initialize the database schema '
                                           '(WARNING: deletes all data!)')
    inp.add_argument('-y', '--yes', help='Must specify this option to initialize')

    stp = sp.add_parser('stats', help='Report stats on loaded data')
    stp.add_argument('-j', '--json', action='store_true',
                     help='Report data as json')

    uip = sp.add_parser('user_info', help='Update / fill in user info table')
    uip, uipgrp = common_arguments(uip)
    uipgrp.add_argument('-l', '--twitter-lists', nargs='+',
                        help='get info for all users in given Twitter lists')

    frp = sp.add_parser('friends',
                        help="Get users' friends (may load new users rows)")
    frp, frpgrp = common_arguments(frp)
    frp.add_argument('-f', '--full', action='store_true',
                     help='Load full user objects (slower)')

    flp = sp.add_parser('followers',
                        help="Get users' followers (may load new users rows)")
    flp, flpgrp = common_arguments(flp)
    flp.add_argument('-f', '--full', action='store_true',
                     help='Load full user objects (slower)')

    twp = sp.add_parser('tweets', help='Get user timeline')
    twp, twpgrp = common_arguments(twp)
    twp.add_argument('-o', '--old-tweets', action='store_true',
                     help="Load tweets older than user's most recent in DB")
    twp.add_argument('-c', '--since-timestamp',
                     help='ignore tweets older than this Unix timestamp')
    twp.add_argument('-r', '--max-tweets',
                     help='max number of tweets to collect')
    twp.add_argument('-f', '--full', action='store_true',
                     help='Load full user objects (slower)')
    twp.add_argument('-t', '--tweet-tag',
                     help='Tag to apply to loaded tweets')

    args = parser.parse_args()

    verbose = ut.coalesce(vars(args).pop('verbose'), 0)
    twurlrc = vars(args).pop('twurlrc')
    command = vars(args).pop('command')

    if command != 'stats' and args.user_spec == 'missing':
        vars(args)['user_spec'] = 'missing_' + args.command

    if command != 'stats':
        auths = ut.get_twitter_auth(filename=twurlrc)
        kwargs = dict(vars(args), **{'auths': auths})

    ##
    ## Set up logging
    ##

    if verbose == 0:
        lvl = logging.WARNING
    elif verbose == 1:
        lvl = logging.INFO
    else: # verbose >= 2
        lvl = logging.DEBUG

    fmt = '%(asctime)s : %(module)s : %(levelname)s : %(message)s'
    logging.basicConfig(format=fmt, level=lvl)

    ##
    ## Do requested work
    ##

    if command == 'initialize':
        yes = vars(args).pop('yes')

        if not yes:
            logger.warning("WARNING: This command will drop the Twitter data "
                           "schema and delete all data! If you want to "
                           "proceed, rerun with '-y'.")
        else:
            job = InitializeJob(**kwargs)

            job.run()
    if command == 'stats':
        use_json = vars(args).pop('json')
        kwargs = vars(args)

        job = StatsJob(**kwargs)
        stats = job.run()

        if use_json:
            msg = json.dumps(stats, indent=4)
        else:
            msg = '\n'.join([
                k.replace('_', ' ').capitalize() + ': ' + str(stats[k])
                for k in stats
            ])

        print(msg)
    elif command == 'user_info':
        job = UserInfoJob(**kwargs)

        job.run()
    elif command in ('friends', 'followers'):
        kwargs = dict(kwargs, **{'direction': command})
        job = FollowJob(**kwargs)

        job.run()
    else: # command == 'tweets'
        job = TweetsJob(**kwargs)

        job.run()

if __name__ == '__main__':
    main()

