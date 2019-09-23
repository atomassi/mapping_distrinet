"""
First Fit Ordered Deviation heuristic from [2]

[2]  Han, Bernard T., George Diehr, and Jack S. Cook.
    "Multiple-type, two-dimensional bin packing problems: Applications and algorithms."
    Annals of Operations Research 50.1 (1994): 239-261.
"""
import logging

from distriopt.constants import *
from distriopt.decorators import timeit
from distriopt.packing import PackingSolver
from distriopt.packing.solution import Solution
from .utils import Bin


_log = logging.getLogger(__name__)


class FirstFitOrderedDeviation(PackingSolver):
    @timeit
    def solve(self, **kwargs):
        # items sorted in non-increasing order
        sorted_items = sorted(
            self.virtual.nodes(),
            key=lambda u: abs(
                self.virtual.req_memory(u) - 1000 * self.virtual.req_cores(u)
            )
            / (self.virtual.req_memory(u) + 1000 * self.virtual.req_cores(u)),
        )

        bins = []

        for u in sorted_items:
            req_cores, req_memory = (
                self.virtual.req_cores(u),
                self.virtual.req_memory(u),
            )

            # cost of the cheapest new bin
            type_cheapest_new, cost_cheapest_new = min(
                (
                    (
                        t,
                        self.physical.hourly_cost(t)
                        * max(
                            req_cores / float(self.physical.cores(t)),
                            req_memory / float(self.physical.memory(t)),
                        ),
                    )
                    for t in self.physical.vm_options
                    if req_cores <= self.physical.cores(t)
                    and req_memory <= self.physical.memory(t)
                ),
                key=lambda x: x[1],
            )

            try:
                # cost cheapest already opened bin
                cheapest_opened, cost_cheapest_opened = min(
                    (
                        (
                            bin,
                            self.physical.hourly_cost(bin.vm_type)
                            * (
                                max(
                                    req_cores / float(self.physical.cores(bin.vm_type)),
                                    req_memory
                                    / float(self.physical.memory(bin.vm_type))
                                    - bin.used_cores
                                    / float(self.physical.cores(bin.vm_type))
                                    + bin.used_memory
                                    / float(self.physical.memory(bin.vm_type)),
                                )
                                if bin.used_cores
                                / float(self.physical.cores(bin.vm_type))
                                > bin.used_memory
                                / float(self.physical.memory(bin.vm_type))
                                else max(
                                    req_memory
                                    / float(self.physical.memory(bin.vm_type)),
                                    req_cores / float(self.physical.cores(bin.vm_type))
                                    + bin.used_cores
                                    / float(self.physical.cores(bin.vm_type))
                                    - bin.used_memory
                                    / float(self.physical.memory(bin.vm_type)),
                                )
                            ),
                        )
                        for bin in bins
                        if req_cores + bin.used_cores
                        <= self.physical.cores(bin.vm_type)
                        and req_memory + bin.used_memory
                        <= self.physical.memory(bin.vm_type)
                    ),
                    key=lambda x: x[1],
                )

            except ValueError:
                cheapest_opened = None

            if (
                cheapest_opened is not None
                and cost_cheapest_opened <= cost_cheapest_new
            ):
                cheapest_opened.add_item(u, req_cores, req_memory)
            else:
                new_bin = Bin(type_cheapest_new)
                new_bin.add_item(u, req_cores, req_memory)
                bins.append(new_bin)

        self.solution = Solution.build_solution(
            self.virtual,
            self.physical,
            {(bin.vm_type, i): bin.items for i, bin in enumerate(bins)},
        )
        self.status = Solved
        return Solved
