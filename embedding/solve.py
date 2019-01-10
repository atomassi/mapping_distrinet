"""
Base class
"""
import logging
import time
from abc import abstractmethod, ABCMeta


class Embed(object, metaclass=ABCMeta):

    def __init__(self, logical_topo, physical_topo):
        self.logical = logical_topo.g
        self.physical = physical_topo.g
        # dict: key is the logical node, value is the physical node e.g., {i:a,j:b}
        self.res_node_mapping = {}
        # dict: key is the logical link, value is a dict with the physical links and the ratio of flows on it, e.g., {(i,j):{(a,b):1, (b,c):0.5, (b,d):0.5, (c,e}:0.5, (d,e):0.5}
        self.res_link_mapping = {}
        self._log = logging.getLogger(__name__)

    @staticmethod
    def timeit(f):
        def timed(*args, **kwargs):
            start = time.time()
            result = f(*args, **kwargs)
            end = time.time()
            # print(f"TIME:  {f.__name__} {round((end - start), 3)} s")
            return end - start, result

        return timed

    @abstractmethod
    def __call__(self, **kwargs):
        """This method must be implemented"""

    def verify_solution(self):
        """check if the solution is correct
        """

        # each logical node is assigned
        # cpu limit is not exceeded
        # memory limit is not exceeded
        # each logical link is mapped on a path
        # link rate limit is not exceeded
        # delay requirements are respected

        # @todo
        # raise NotImplementedError
