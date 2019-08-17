"""
Base class.
"""
import logging
import math
from abc import abstractmethod, ABCMeta

from mininet.topo import Topo

from distriopt import VirtualNetwork
from distriopt.constants import *
from distriopt.embedding import PhysicalNetwork

_log = logging.getLogger(__name__)


class EmbedSolver(object, metaclass=ABCMeta):
    def __init__(self, virtual, physical):
        """"""
        self.virtual = (
            VirtualNetwork.from_mininet(virtual)
            if isinstance(virtual, Topo)
            else virtual
        )
        self.physical = (
            PhysicalNetwork.from_mininet(physical)
            if isinstance(physical, Topo)
            else physical
        )
        self.solution = None
        self.status = NotSolved

    def lower_bound(self):
        """Return a lower bound on the minimum number of physical machines needed to map all the virtual nodes."""
        tot_req_cores = tot_req_memory = 0
        for virtual_node in self.virtual.nodes():
            # the total number of cores to be mapped
            tot_req_cores += self.virtual.req_cores(virtual_node)
            # the total required memory to be mapped
            tot_req_memory += self.virtual.req_memory(virtual_node)

        max_phy_memory = max_phy_cores = 0
        for phy_node in self.physical.compute_nodes:
            # the maximum capacity in terms of cores for a physical machine
            max_phy_cores = (
                self.physical.cores(phy_node)
                if self.physical.cores(phy_node) > max_phy_cores
                else max_phy_cores
            )
            # the maximum capacity in terms of memory for a physical machine
            max_phy_memory = (
                self.physical.memory(phy_node)
                if self.physical.memory(phy_node) > max_phy_memory
                else max_phy_memory
            )

        # lower bound, any feasible mapping requires at least this number of physical machines
        return math.ceil(
            max(tot_req_cores / max_phy_cores, tot_req_memory / max_phy_memory)
        )

    @abstractmethod
    def solve(self, **kwargs):
        """This method must be implemented."""
