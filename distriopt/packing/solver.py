"""
Base class
"""
import logging
from abc import abstractmethod, ABCMeta
from functools import lru_cache

from mininet.topo import Topo

from distriopt import VirtualNetwork
from distriopt.constants import *

_log = logging.getLogger(__name__)


class PackingSolver(object, metaclass=ABCMeta):
    def __init__(self, virtual, physical):
        """"""
        self.virtual = (
            VirtualNetwork.from_mininet(virtual)
            if isinstance(virtual, Topo)
            else virtual
        )
        self.physical = physical
        self.solution = None
        self.status = NotSolved
        self.lb = 0

    def _get_ub(self, vm_type):
        """Return an upper bound on the maximum number of EC2 instances of type vm_type needed to pack all the nodes"""

        cpu_cores_instance, memory_instance = (
            self.physical.cores(vm_type),
            self.physical.memory(vm_type),
        )
        n_instances_needed = remaining_cpu_cores = remaining_memory = 0
        for u in self.virtual.nodes():
            req_cores, req_memory = (
                self.virtual.req_cores(u),
                self.virtual.req_memory(u),
            )
            if req_cores <= remaining_cpu_cores and req_memory <= remaining_memory:
                remaining_cpu_cores -= req_cores
                remaining_memory -= req_memory
            elif req_cores <= cpu_cores_instance and req_memory <= memory_instance:
                remaining_cpu_cores = cpu_cores_instance - req_cores
                remaining_memory = memory_instance - req_memory
                n_instances_needed += 1
        return n_instances_needed

    def _get_feasible_instances(self, u):
        """Return a set with the instances types feasible for node u
        """
        return set(
            vm_type
            for vm_type in self.physical.vm_options
            if self.virtual.req_cores(u) <= self.physical.cores(vm_type)
            and self.virtual.req_memory(u) <= self.physical.memory(vm_type)
        )

    @lru_cache(maxsize=256)
    def _get_cheapest_feasible(self, cores, memory):
        """Given a demand in terms of number of cores and memory return the cheapest EC2 instance with enough resources.
        """
        # if (cores > self.physical.cores(self.vm_max_cores) or memory > self.physical.memory(self.vm_max_cores)) \
        #        and (
        #        cores > self.physical.cores(self.vm_max_memory) or memory > self.physical.memory(self.vm_max_memory)):
        #    return None

        return min(
            (
                (vm, self.physical.hourly_cost(vm))
                for vm in self.physical.vm_options
                if cores <= self.physical.cores(vm)
                and memory <= self.physical.memory(vm)
            ),
            key=lambda x: x[1],
        )[0]

    @abstractmethod
    def solve(self, **kwargs):
        """This method must be implemented"""
