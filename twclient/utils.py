import re
import logging

logger = logging.getLogger(__name__)

def uniq(it):
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

    for s in it:
        if not s in seen:
            ret += [s]
            seen.add(s)

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
    object, or None
        Returns the first non-None argument, or None.
    '''

    try:
        return next(filter(lambda x: x is not None, args))
    except StopIteration:
        return None

# Generate chunks of size n from the iterable it
def grouper(it, n=None):
    '''
    Generate chunks of size n from the iterable it.

    This function takes the iterable it n elements at a time, returning each
    chunk of n elements as a list. If n is None, return the entire iterable at
    once as a list.

    Parameters
    ----------
    it : iterable
        The iterable to chunk.

    n : int, or None
        The size of each chunk.

    Returns
    -------
    generator
        The contents of iterable it, n at a time.
    '''

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

def split_camel_case(s):
    '''
    Turn a CamelCase VariableName into a list of component words.

    For example, turns UserDataTableName into ['User', 'Data', 'Table', 'Name'].

    Parameters
    ----------
    s : str
        An input string

    Returns
    -------
    list of str
        The component words
    '''

    return re.sub('([A-Z]+)', r' \1', s).split()

