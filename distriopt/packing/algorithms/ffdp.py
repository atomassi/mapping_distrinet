"""
First Fit Decreasing heuristic from [1]

[1]  Silva, Pedro, Christian Perez, and Frédéric Desprez.
    "Efficient heuristics for placing large-scale distributed applications on multiple clouds."
     2016 16th IEEE/ACM International Symposium on Cluster, Cloud and Grid Computing (CCGrid). IEEE, 2016.
"""
import logging

from distriopt.constants import *
from distriopt.decorators import timeit
from distriopt.packing import PackingSolver
from distriopt.packing.solution import Solution

log = logging.getLogger(__name__)


class Bin(object):
    """ Container for virtual nodes mapped on the Bin associated to a VM """

    def __init__(self, vm_type):
        self.vm_type = vm_type
        self.items = set()
        self.used_cores = 0
        self.used_memory = 0

    def add_item(self, u, req_cores, req_memory):
        self.items.add(u)
        self.used_cores += req_cores
        self.used_memory += req_memory

    def __str__(self):
        """ Printable representation """
        return f"Bin(vm_type={self.vm_type}, items={self.items}, used cores={self.used_cores}, used memory={self.used_memory})"


class FirstFitDecreasingPriority(PackingSolver):
    @timeit
    def solve(self, **kwargs):
        # items sorted in non-increasing order
        sorted_items = sorted(
            self.virtual.nodes(),
            key=lambda x: self.virtual.req_cores(x) * 1000 + self.virtual.req_memory(x),
            reverse=True,
        )

        # coefficient
        alpha = {
            "cores": sum(self.virtual.req_cores(u) for u in self.virtual.nodes())
            / float(sum(self.physical.cores(vm) for vm in self.physical.vm_options)),
            "memory": sum(self.virtual.req_memory(u) for u in self.virtual.nodes())
            / float(sum(self.physical.memory(vm) for vm in self.physical.vm_options)),
        }

        sorted_bin_types = sorted(
            self.physical.vm_options,
            key=lambda x: 1
            / float(self.physical.hourly_cost(x))
            * (
                alpha["cores"] * 1000 * self.physical.cores(x)
                + alpha["memory"] * self.physical.memory(x)
            ),
            reverse=True,
        )

        bins = []
        for u in sorted_items:
            req_cores, req_memory = (
                self.virtual.req_cores(u),
                self.virtual.req_memory(u),
            )

            try:
                selected_bin = max(
                    (
                        bin
                        for bin in bins
                        if bin.used_cores + req_cores
                        <= self.physical.cores(bin.vm_type)
                        and bin.used_memory + req_memory
                        <= self.physical.memory(bin.vm_type)
                    ),
                    key=lambda x: 1
                    / float(self.physical.hourly_cost(x.vm_type))
                    * (
                        sum(
                            alpha["cores"] * 1000 * self.virtual.req_cores(v)
                            for v in x.items
                        )
                        + sum(
                            alpha["memory"] * self.virtual.req_memory(v)
                            for v in x.items
                        )
                    ),
                )
                # print(selected_bin.vm_type)
                selected_bin.add_item(u, req_cores, req_memory)
            except ValueError:
                bin_to_open = next(
                    (
                        bin_type
                        for bin_type in sorted_bin_types
                        if req_cores <= self.physical.cores(bin_type)
                        and req_memory <= self.physical.memory(bin_type)
                    ),
                    None,
                )
                if bin_to_open is None:
                    self.status = Infeasible
                    return Infeasible
                # print(bin_to_open)
                new_bin = Bin(bin_to_open)
                new_bin.add_item(u, req_cores, req_memory)
                bins.append(new_bin)

        self.solution = Solution.build_solution(
            self.virtual,
            self.physical,
            {(bin.vm_type, i): bin.items for i, bin in enumerate(bins)},
        )
        self.status = Solved
        return Solved
