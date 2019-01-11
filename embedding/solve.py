"""
Base class
"""
import logging
import time
from abc import abstractmethod, ABCMeta
from collections import defaultdict

from exceptions import EmptySolutionError, AssignmentError, NodeResourceError, LinkCapacityError


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
        #
        # empty solution or invalid solution
        #
        if not self.res_node_mapping or not self.res_link_mapping:
            raise EmptySolutionError
        #
        # each logical node is assigned to a physical node
        #
        self._log.info("\nLOGICAL NODES")
        for logical_node in self.logical.nodes():
            if not logical_node in self.res_node_mapping:
                raise AssignmentError(logical_node)
            else:
                self._log.info(f"Logical Node {logical_node} assigned to {self.res_node_mapping[logical_node]}")
        self._log.info("\nLOGICAL LINKS")
        #
        # each logical link is assigned
        #
        for logical_link in self.logical.edges():
            (u,v) = logical_link
            if not logical_link in self.res_link_mapping and self.res_node_mapping[u] != self.res_node_mapping[v]:
                raise AssignmentError(logical_link)
            elif self.res_node_mapping[u] != self.res_node_mapping[v]:
                sum_rate = 0
                for (source_node, source_interface, dest_node, dest_interface, rate_on_it) in self.res_link_mapping[(u,v)]:
                    sum_rate += rate_on_it
                    if source_node != self.res_node_mapping[u] or dest_node != self.res_node_mapping[v]:
                        raise AssignmentError(logical_link)
                if sum_rate != 1:
                    raise AssignmentError(logical_link)

        #
        # resource usage on nodes
        #
        # dict -> physical node: CPU cores used on it
        cpu_used_node = defaultdict(int)
        # dict -> physical node: memory used on it
        memory_used_node = defaultdict(int)
        # compute resources used
        for logical_node, physical_node in self.res_node_mapping.items():
            cpu_used_node[physical_node] += self.logical.nodes[logical_node]['cpu_cores']
            memory_used_node[physical_node] += self.logical.nodes[logical_node]['memory']
        # cpu limit is not exceeded
        self._log.info("\nCPU Cores")
        for physical_node, cpu_cores_used in cpu_used_node.items():
            node_cores = self.physical.nodes[physical_node]['nb_cores']
            self._log.info(f"Physical Node {physical_node}: cpu cores used {cpu_cores_used} capacity {node_cores}")
            if cpu_cores_used > self.physical.nodes[physical_node]['nb_cores']:
                raise NodeResourceError(physical_node, "cpu cores", cpu_cores_used, node_cores)
        # memory limit is not exceeded
        self._log.info("\nMEMORY")
        for physical_node, memory_used in memory_used_node.items():
            node_memory = self.physical.nodes[physical_node]['ram_size']
            self._log.info(f"Physical Node {physical_node}: memory used {memory_used} capacity {node_memory}")
            if memory_used > self.physical.nodes[physical_node]['ram_size']:
                raise NodeResourceError(physical_node, "memory", memory_used, node_memory)
        #
        # resource usage on links
        #
        # dict -> physical link: rate used on it
        # @todo

        # delay requirements are respected
        # @todo to be defined
