import re
import logging

logger = logging.getLogger(__name__)

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

def split_camel_case(s):
    return re.sub('([A-Z]+)', r' \1', s).split()

