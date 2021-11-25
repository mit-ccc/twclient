'''
Shared configuration for twclient tests.
'''

import os

import vcr


bearer_token = os.environ.get('BEARER_TOKEN', '')
consumer_key = os.environ.get('CONSUMER_KEY', '')
consumer_secret = os.environ.get('CONSUMER_SECRET', '')
access_token = os.environ.get('ACCESS_TOKEN', '')
access_token_secret = os.environ.get('ACCESS_TOKEN_SECRET', '')

replay = os.environ.get('TEST_REPLAY', True)

tape = vcr.VCR(
    cassette_library_dir='cassettes',
    filter_headers=['Authorization'],
    serializer='json',
    record_mode='none' if replay else 'all',
)
