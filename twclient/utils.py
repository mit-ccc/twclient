'''
Utilities for other parts of twclient
'''

import re
import json
import logging

logger = logging.getLogger(__name__)


def uniq(iterable):
    '''
    Deduplicate an interable, preserving original order.

    This function removes second and subsequent occurrences of values which
    occur more than once in some iterable, without changing the order of the
    retained values.

    Parameters
    ----------
    it : iterable
        An iterable, including a generator. Need not support restartable
        iteration.

    Returns
    -------
    list
        The contents of the deduplicated iterable in the order encountered.
    '''

    seen, ret = set(), []

    for val in iterable:
        if val not in seen:
            ret += [val]
            seen.add(val)

    return ret


def coalesce(*args):
    '''
    Return the first argument that's not None.

    This function mimics the coalesce() function in standard SQL, by returning
    the first argument given to it that's not None. If all arguments are None,
    or if no arguments are provided, returns None.

    Parameters
    ----------
    *args : positional arguments
        Objects to test for being None.

    Returns
    -------
    object
        Returns the first non-None argument, or None.
    '''

    try:
        present = iter([x for x in args if x is not None])
        return next(present)
    except StopIteration:
        return None


# Generate chunks of size n from the iterable it
def grouper(iterable, chunk_size=None):
    '''
    Generate chunks of size n from the iterable iterable.

    This function takes the iterable iterable n elements at a time, returning
    each chunk of n elements as a list. If n is None, return the entire
    iterable at once as a list.

    Parameters
    ----------
    iterable : iterable
        The iterable to chunk.

    n : int, or None
        The size of each chunk.

    Yields
    ------
    list
        A list of n consecutive elements from the iterable iterable.
    '''

    try:
        assert chunk_size is None or chunk_size > 0
    except AssertionError as exc:
        raise ValueError('Bad chunk_size value for grouper') from exc

    if chunk_size is None:
        yield iterable
    else:
        ret = []

        for obj in iterable:
            if len(ret) == chunk_size:
                yield ret
                ret = []

            if len(ret) < chunk_size:
                ret += [obj]

        # at this point, we're out of
        # objects but len(ret) < chunk_size
        if ret:
            yield ret


def split_camel_case(txt):
    '''
    Turn a CamelCase VariableName into a list of component words.

    For example, turn UserDataTableName into ['User', 'Data', 'Table', 'Name'].

    Parameters
    ----------
    s : str
        An input string

    Returns
    -------
    list of str
        The component words
    '''

    return re.sub('([A-Z]+)', r' \1', txt).split()


# There's no good way to do this except accessing the _json attribute on a
# tweepy Model instance. The JSONParser class in tweepy is poorly documented
# and breaks some things that are possible without it, so we're left with this.
# As of Sept 2020, this attribute is just the same json passed to the Model's
# classmethod constructor - should really be public API.
def tweepy_to_json(obj):
    '''
    Convert a tweepy object to json.

    Parameters
    ----------
    obj : tweepy.Model instance
        The tweepy object to convert to json.

    Returns
    -------
    str
        A json representation of obj.
    '''

    return json.dumps(obj._json)  # pylint: disable=protected-access
