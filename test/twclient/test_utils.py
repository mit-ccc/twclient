'''
Tests for utils.py
'''

from src.twclient._utils import uniq

def test_uniq():
    '''
    Test twclient.utils.uniq
    '''

    assert uniq([1,1,2,2,3,3,4,4]) == [1, 2, 3, 4]
    assert uniq([1,2,1,5,9,7,4,4]) == [1,2,5,9,7,4]
