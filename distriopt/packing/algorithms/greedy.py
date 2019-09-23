import logging

from distriopt.constants import *
from distriopt.decorators import timeit
from distriopt.packing import PackingSolver
from distriopt.packing.solution import Solution
from .utils import Bin

_log = logging.getLogger(__name__)


class PackGreedy(PackingSolver):
    @timeit
    def solve(self, **kwargs):
        """
        """
        self.vm_max_cores = max(
            self.physical.vm_options, key=lambda vm: self.physical.cores(vm)
        )
        self.vm_max_memory = max(
            self.physical.vm_options, key=lambda vm: self.physical.memory(vm)
        )

        bins = []
        for u in self.virtual.nodes():
            req_cores, req_memory = (
                self.virtual.req_cores(u),
                self.virtual.req_memory(u),
            )
            # Check if the item fits in an already opened bin.
            # In such a case, it adds the virtual node to the item list and update resources usage.
            for bin in bins:
                if bin.used_cores + req_cores <= self.physical.cores(
                    bin.vm_type
                ) and bin.used_memory + req_memory <= self.physical.memory(bin.vm_type):
                    bin.add_item(u, req_cores, req_memory)
                    break
            else:
                # Check if it is convenient to upgrade a bin type.
                # To this end, given an item u and bin b it gets
                # - the cheapest available bin b' with enough resources to contain the items of b and u
                # - the cheapest available bin b'' with enough resources to contain i
                # If the cost of b' is smaller than the cost of b upgrade b to b', otherwise keep b and open b''.
                vm_to_pack_u = self._get_cheapest_feasible(req_cores, req_memory)
                for bin in reversed(bins):
                    vm_to_upgrade = self._get_cheapest_feasible(
                        req_cores + bin.used_cores, req_memory + bin.used_memory
                    )
                    if vm_to_upgrade and self.physical.hourly_cost(
                        vm_to_upgrade
                    ) < self.physical.hourly_cost(
                        vm_to_pack_u
                    ) + self.physical.hourly_cost(
                        bin.vm_type
                    ):
                        bin.vm_type = vm_to_upgrade
                        bin.add_item(u, req_cores, req_memory)
                        break
                else:
                    # Open a new bin b'' and insert u on it.
                    new_bin = Bin(vm_to_pack_u)
                    new_bin.add_item(u, req_cores, req_memory)
                    bins.append(new_bin)
        # print(self._get_cheapest_feasible.cache_info())
        self.solution = Solution.build_solution(
            self.virtual,
            self.physical,
            {(bin.vm_type, i): bin.items for i, bin in enumerate(bins)},
        )
        self.status = Solved
        return Solved
