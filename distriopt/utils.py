import time


def timeit(f):
    def timed(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        end = time.time()
        return end - start, result

    return timed


class CachedFunction:
    def __init__(self, f):
        self.f = f
        self._cache = {}

    def __call__(self, *args):
        try:
            return self._cache[args]
        except KeyError:
            res = self._cache[args] = self.f(*args)
            return res
