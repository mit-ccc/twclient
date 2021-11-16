'''
Tests for utils.py.
'''

import pytest
from twclient import _utils as ut


def test_split_camel_case():
    with pytest.raises(TypeError):
        ut.split_camel_case(None)

    assert ut.split_camel_case('') == []
    assert ut.split_camel_case('foobarbazquux') == ['foobarbazquux']
    assert ut.split_camel_case('Foobarbazquux') == ['Foobarbazquux']
    assert ut.split_camel_case('FooBarbazquux') == ['Foo', 'Barbazquux']
    assert ut.split_camel_case('FooBarBazQuux') == ['Foo', 'Bar', 'Baz',
                                                    'Quux']
