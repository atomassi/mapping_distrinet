"""
Base class
"""
import logging
import math
from abc import abstractmethod, ABCMeta


class Embed(object, metaclass=ABCMeta):

    def __init__(self):
        self._log = logging.getLogger(__name__)

    def _get_lb(self, virtual, physical):
        """Return a lower bound on the minimum number of physical machines needed to map all the virtual nodes."""

        # nodes able to host VMs
        compute_nodes = physical.compute_nodes

        tot_req_cores = tot_req_memory = 0
        for virtual_node in virtual.nodes():
            # the total number of cores to be mapped
            tot_req_cores += virtual.req_cores(virtual_node)
            # the total required memory to be mapped
            tot_req_memory += virtual.req_memory(virtual_node)

        max_phy_memory = max_phy_cores = 0
        for phy_node in compute_nodes:
            # the maximum capacity in terms of cores for a physical machine
            max_phy_cores = physical.cores(phy_node) if physical.cores(
                phy_node) > max_phy_cores else max_phy_cores
            # the maximum capacity in terms of memory for a physical machine
            max_phy_memory = physical.memory(phy_node) if physical.memory(
                phy_node) > max_phy_memory else max_phy_memory

        # lower bound, any feasible mapping requires at least this number of physical machines
        return math.ceil(max(tot_req_cores / max_phy_cores, tot_req_memory / max_phy_memory))

    @abstractmethod
    def __call__(self, virtual, physical, **kwargs):
        """This method must be implemented"""
