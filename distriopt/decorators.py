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


def cachedproperty(func):
    """Decorator to cache property values."""
    values = {}

    @property
    @functools.wraps(func)
    def wrapper(self):
        if self not in values:
            values[self] = func(self)
        return values[self]

    return wrapper


def implemented_if_true(name):
    """Raise a ValueError exception if called when self.name is set to False."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.__dict__[name]:
                raise ValueError(f"{name} is not set to True.")
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
