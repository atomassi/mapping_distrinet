"""
Contains decorators used in the module.
"""
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


def cached(func):
    """Decorator to cache the result of a function call."""

    func.cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs:
            key = args, frozenset(kwargs.items())
        else:
            key = args
        if key not in func.cache:
            func.cache[key] = func(*args, **kwargs)
        return func.cache[key]

    return wrapper


