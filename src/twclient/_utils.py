'''
Utilities for other parts of twclient.
'''

import re
import sys
import json
import gzip
import logging
import contextlib

from packaging import version

import tweepy as tp
import sqlalchemy as sa

logger = logging.getLogger(__name__)


# Version checks for elsewhere
TWEEPY_V4 = version.parse(tp.__version__) >= version.parse('4.0.0')
TWEEPY_V45 = version.parse(tp.__version__) >= version.parse('4.5.0')
SA_V14 = version.parse(sa.__version__) >= version.parse('1.4.0')
SA_V20 = version.parse(sa.__version__) >= version.parse('2.0.0')

# c/o https://stackoverflow.com/questions/44834/can-someone-explain-all-in-python
def export(obj):
    '''
    A decorator which adds the decorated object to its module's __all__.
    '''

    mod = sys.modules[obj.__module__]

    if hasattr(mod, '__all__'):
        mod.__all__.append(obj.__name__)
    else:
        mod.__all__ = [obj.__name__]

    return obj


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


def gzip_safe_open(fle, mode='rt'):
    '''
    Open a file, handling ``.gz`` files transparently.

    Works like the builtin ``open()`` but will use either ``open()`` or
    ``gzip.open()`` depending on whether the file has a ``.gz`` extension.

    Parameters
    ----------
    fle : str
        The path to a file to open.

    mode : str
        The open mode (default 'rt').

    Returns
    -------
    file-like object
        The opened file.
    '''

    if fle.lower().endswith('.gz'):
        func = gzip.open
    else:
        func = open

    return func(fle, mode)


@contextlib.contextmanager
def smart_open(filename='-', mode='rt', func=gzip_safe_open):
    '''
    Open a file, handling gzip and the use of '-' to refer to stdin or stdout.

    This function, which is usable as a context manager, opens a file with
    special semantics around the use of filename '-' to refer to stdin or
    stdout. If this special filename is given, either sys.stdin or sys.stdout
    will be returned depending on the open mode, with no new file handles being
    opened; if another value is passed, that file will be opened as usual. More
    specifically, if '-' is passed and ``mode.startswith('r')``, sys.stdin will
    be returned, while if '-' is passed and mode starts with any character but
    'r', sys.stdout will be returned. (This is because it doesn't make sense to
    read from stdout or write to stdin.) Any characters in the open mode after
    the first will be ignored in this case.

    The ``smart_open`` function allows use of a customizable open function, not
    just the builtin ``open()``, so that one can, for example, open gzipped
    files. The default function is ``gzip_safe_open``, which uses
    ``gzip.open()`` for ``.gz`` files and ``open()`` for other files.

    Parameters
    ----------
    filename : str
        The path to a file to open, or '-'.

    mode : str
        The open mode.

    func : callable
        The function to call to open the file.

    Returns
    -------
    file-like object
        The (possibly) opened file, which may be sys.stdin or sys.stdout.
    '''

    is_read = mode.startswith('r')

    if filename and filename != '-':
        handle = func(filename, mode)
    elif is_read:
        handle = sys.stdin
    else:
        # it doesn't make sense to ask for read on stdout or write on
        # stdin, so '-' can be unambiguously resolved to one or the other
        # depending on the open mode
        handle = sys.stdout

    try:
        yield handle
    finally:
        if is_read and handle is not sys.stdin:
            handle.close()
        elif not is_read and handle is not sys.stdout:
            handle.close()
