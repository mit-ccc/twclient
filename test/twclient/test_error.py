'''
Tests for twclient.error.
'''

# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring

import inspect

from src.twclient import error


def test_basic():
    err = error.TWClientError(message='test test test', exit_status=127)

    assert hasattr(err, 'message') and err.message == 'test test test'
    assert hasattr(err, 'exit_status') and err.exit_status == 127

    err = error.BadTagError(tag='TestTag')
    assert hasattr(err, 'tag') and err.tag == 'TestTag'

    err = error.BadTargetError(targets=['just', 'an', 'example'])
    assert hasattr(err, 'targets') and err.targets == ['just', 'an', 'example']


def test_inheritance():
    # All subclasses of a single root
    klasses = [
        m[1]
        for m in inspect.getmembers(error, inspect.isclass)
        if m[1].__module__ == 'error' and m[0] != 'TWClientError'
    ]

    assert all(issubclass(m, error.TWClientError) for m in klasses)

    assert issubclass(error.TwitterServiceError, error.TwitterAPIError)
    assert issubclass(error.TwitterLogicError, error.TwitterAPIError)

    assert issubclass(error.NotFoundError, error.TwitterLogicError)
    assert issubclass(error.ForbiddenError, error.TwitterLogicError)

    assert issubclass(error.BadTargetError, error.SemanticError)
    assert issubclass(error.BadTagError, error.SemanticError)
    assert issubclass(error.BadSchemaError, error.SemanticError)
