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
            if not logical_link in self.res_link_mapping:
                raise AssignmentError(logical_link)
            else:
                self._log.info(f"Logical Link {logical_link} assigned to {self.res_link_mapping[logical_link]}")

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
        rate_used_link = defaultdict(int)

        for logical_link, map_physical_links in self.res_link_mapping.items():
            (u, v) = logical_link
            for physical_link, rate_on_it in map_physical_links.items():
                (i, j, device) = physical_link
                rate_used_link[(i, j, device)] += self.logical[u][v]['bw'] * rate_on_it
        # link rate limit is not exceeded
        self._log.info("\nLINK RATE")
        for physical_link, rate_used in rate_used_link.items():
            (i, j, device) = physical_link
            link_rate = self.physical[i][j][device]['rate']
            self._log.info(
                f"Physical Link {physical_link}: used {rate_used / 10 ** 6} Mbps capacity {link_rate / 10 ** 6} Mbps")
            if rate_used > link_rate:
                raise LinkCapacityError(physical_link, rate_used, link_rate)

        #
        # each logical link is mapped on a valid path
        #
        # N.B. a logical link may be splitted on multiple physical links, I assume for the moment that it cannot
        # build a path
        for logical_link in self.res_link_mapping:
            (u, v) = logical_link
            map_physical_links = self.res_link_mapping[logical_link]
            if not self.res_link_mapping[logical_link].keys() and self.res_node_mapping[u] != self.res_node_mapping[v]:
                raise AssignmentError(logical_link)
            elif self.res_node_mapping[u] == self.res_node_mapping[v]:
                self._log.info(f"Logical Link {logical_link} not mapped (endpoints in the same physical machines)")
            else:
                source_node, dest_node = self.res_node_mapping[u], self.res_node_mapping[v]
                source_path = dest_path = None
                for (i, j, device) in map_physical_links:
                    if i == source_node:
                        source_path = (i, device)
                    elif j == source_node:
                        source_path = (j, device)
                    elif i == dest_node:
                        dest_path = (i, device)
                    elif j == dest_node:
                        dest_path = (j, device)
                if not source_path or not dest_path:
                    print(source_node, dest_node, map_physical_links)
                    raise AssignmentError(logical_link)
                else:
                    self._log.info(f"logical link {logical_link} from {u} to {v} assigned to {source_path, dest_path}")

        # delay requirements are respected
        # @todo to be defined
