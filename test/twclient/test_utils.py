'''
Tests for twclient._utils
'''

# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring


import pytest

from src.twclient import _utils as ut


def test_split_camel_case():
    with pytest.raises(TypeError):
        ut.split_camel_case(None)

    assert ut.split_camel_case('') == []
    assert ut.split_camel_case('foobarbazquux') == ['foobarbazquux']
    assert ut.split_camel_case('Foobarbazquux') == ['Foobarbazquux']
    assert ut.split_camel_case('FooBarbazquux') == ['Foo', 'Barbazquux']
    assert ut.split_camel_case('FooBarBazQuux') == ['Foo', 'Bar', 'Baz',
                                                    'Quux']

def test_uniq():
    with pytest.raises(TypeError):
        ut.uniq(None)

    it1 = [1,1,2,2,3,3,5,8,9]
    it2 = [2,4,5,5,6,7,8,1,3,8,6,5,5,6]

    it3 = ['a', 'b', 'c', 'd', 'e', 'f']
    it4 = ['a', 'a', 'c', 'b', 'b', 'z', 'e', 'f', 'f', 'a', 'g', 'g', 'g']


    assert ut.uniq(it1) == [1,2,3,5,8,9]
    assert ut.uniq(it2) == [2,4,5,6,7,8,1,3]

    assert ut.uniq(it3) == ['a', 'b', 'c', 'd', 'e', 'f']
    assert ut.uniq(it4) == ['a', 'c', 'b', 'z', 'e', 'f', 'g']

def test_coalesce():
    assert ut.coalesce(None) is None
    assert ut.coalesce(1, None) == 1
    assert ut.coalesce(None, 2, 1, 3, None) == 2

def test_grouper():
    obj = list(range(20))

    with pytest.raises(ValueError):
        list(ut.grouper(obj, chunk_size=0))

    with pytest.raises(TypeError):
        list(ut.grouper(None, chunk_size=5))

    chunks = list(ut.grouper(obj, chunk_size=None))
    assert chunks == [obj]

    chunks = list(ut.grouper(obj, chunk_size=1))
    assert chunks == [[i] for i in obj]

    chunks = list(ut.grouper(obj, chunk_size=5))
    assert chunks == [[0,1,2,3,4], [5,6,7,8,9], [10, 11, 12, 13, 14],
                      [15,16,17,18,19]]
