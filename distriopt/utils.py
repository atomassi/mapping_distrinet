import functools
import time


def timeit(func):
    """Decorator to measure the time spent by a function."""

    @functools.wraps(func)
    def timed(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        return end - start, result

    return timed


class CachedFunction:
    """Cached Function - useful to store intermediate results."""

    def __init__(self, func):
        self.func = func
        self._cache = {}

    def __call__(self, *args):
        try:
            return self._cache[args]
        except KeyError:
            res = self._cache[args] = self.func(*args)
            return res
