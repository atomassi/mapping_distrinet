"""
Base class
"""
import logging
import time
from abc import abstractmethod, ABCMeta


class Embed(object, metaclass=ABCMeta):

    def __init__(self, logical_topo, physical_topo):
        self.logical_topo = logical_topo
        self.physical_topo = physical_topo
        self._log = logging.getLogger(__name__)

    @staticmethod
    def timeit(f):
        def timed(*args, **kwargs):
            start = time.time()
            result = f(*args, **kwargs)
            end = time.time()
            return end - start, result

        return timed

    @abstractmethod
    def __call__(self, **kwargs):
        """This method must be implemented"""
