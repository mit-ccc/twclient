import os
import csv
import yaml
import string
import random
import logging
import tempfile

import tweepy

fmt = '%(asctime)s : %(module)s : %(levelname)s : %(message)s'
logging.basicConfig(format=fmt, level=logging.INFO)
logger = logging.getLogger(__name__)

# Write datasets to DBs
# data assumed to be a list of dicts
def write_to_tempfile(data, fieldnames=None, mode='r+t',
                      noneval=None, **kwargs):
    if fieldnames is None:
        fieldnames = sorted(list(data[0].keys()))

    # don't use with!
    outfile = tempfile.NamedTemporaryFile(mode=mode, delete=False)
    outwriter = csv.DictWriter(outfile, fieldnames=fieldnames, **kwargs)
    outwriter.writeheader()

    if noneval is not None:
        data = [{k : coalesce(v, noneval) for k, v in row} for row in data]

    outwriter.writerows(data)

    # Make sure the data on disk visible to e.g. a subprocess is right
    outfile.flush()
    outfile.seek(0, 0)

    return outfile

def unique_name_gen(length=10, prefix=''):
    used = set()

    while True:
        cand = ''.join([
            random.choice(string.ascii_lowercase)
            for i in range(length)
        ])

        if cand in used:
            continue
        else:
            used.add(cand)
            yield cand

unique_names = unique_name_gen()

# Like SQL's coalesce() - returns the first argument that's not None
def coalesce(*args):
    try:
        return next(filter(lambda x: x is not None, args))
    except StopIteration:
        return None

# Generate chunks of n from the iterable it
def grouper(it, n=None):
    assert n is None or n > 0

    if n is None:
        yield [x for x in it]
    else:
        ret = []

        for obj in it:
            if len(ret) == n:
                yield ret
                ret = []

            if len(ret) < n:
                ret += [obj]

        # at this point, we're out of
        # objects but len(ret) < n
        if len(ret) > 0:
            yield ret

def get_twitter_auth(filename='~/.twurlrc', app_only=True):
    try:
        rcpath = os.path.expanduser(filename)
        with open(rcpath, 'rt') as f:
            twurlrc = yaml.safe_load(f)
    except FileNotFoundError:
        raise ValueError('No twurlrc found')

    auths = []

    try:
        for user, creds in twurlrc['profiles'].items():
            for credname, cred in creds.items():
                if app_only:
                    auth = tweepy.AppAuthHandler(cred['consumer_key'],
                                                 cred['consumer_secret'])
                else:
                    auth = tweepy.OAuthHandler(cred['consumer_key'],
                                               cred['consumer_secret'])
                    auth.set_access_token(cred['token'], cred['secret'])

                auths += [auth]

                msg = 'Found profile with consumer key {0}'
                logger.debug(msg.format(cred['consumer_key']))

    except KeyError:
        raise ValueError('Malformed ~/.twurlrc or bad profile specification')

    return auths

