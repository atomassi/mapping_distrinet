import math
import random
from collections import defaultdict

from networkx.algorithms.community.kernighan_lin import kernighan_lin_bisection

from embedding.exceptions import NodeResourceError, LinkCapacityError, InfeasibleError
from embedding.solve import Embed
from .solution import Solution

_memo = {}


def get_partitions(g, n_partitions):
    """Given the graph G and the number of partitions k,
       returns a list with k sets of nodes
    """

    def iterative_cutting(g, k, restart_from):
        """helper function
        """

        # to keep track of the computed partitions
        partitions = []

        # if a set of partitions is given as an input restart from them
        # otherwise start with the full graph g
        to_be_processed = restart_from if restart_from else [g]

        # while there is some unprocessed partition get a partitions
        # if the size is smaller than k, append to the result list
        # otherwise partition it
        while len(to_be_processed) > 0:

            p0 = to_be_processed.pop()
            if len(p0) < k:
                partitions.append(p0)
                continue

            for partition in kernighan_lin_bisection(g.subgraph(p0), weight='rate'):
                if len(partition) > k:
                    to_be_processed.append(g.subgraph(partition))
                else:
                    partitions.append(partition)

        return partitions

    k = len(g.nodes()) / n_partitions

    # when computing a paritioning for the graph nodes,
    # if result is known for a smaller value of n_partitions
    # don't restart from scracth but use it as a start value
    if g not in _memo:
        _memo.clear()
    partitions = iterative_cutting(g, k, _memo.get(g, None))
    _memo[g] = partitions

    # merge small partitions to return the required number of parititions
    if len(partitions) > n_partitions:
        while len(partitions) > n_partitions:
            partitions.sort(key=len)
            e1 = partitions.pop(0)
            e2 = partitions.pop(0)
            partitions.append(e1.union(e2))
    return partitions


class EmbedHeu(Embed):

    @Embed.timeit
    def __call__(self, **kwargs):
        """Heuristic based on computing a k-balanced partitions of logical nodes for then mapping the partition
           on a subset of the physical nodes.
        """

        # nodes able to host VMs
        compute_nodes = self.physical.compute_nodes()

        tot_req_cores = tot_req_memory = 0
        for logical_node in self.logical.nodes():
            # the total number of cores to be mapped
            tot_req_cores += self.logical.req_cores(logical_node)
            # the total required memory to be mapped
            tot_req_memory += self.logical.req_memory(logical_node)

        max_phy_memory = max_phy_cores = 0
        for physical_node in compute_nodes:
            # the maximum capacity in terms of cores for a physical machine
            max_phy_cores = self.physical.cores(physical_node) if self.physical.cores(
                physical_node) > max_phy_cores else max_phy_cores
            # the maximum capacity in terms of memory for a physical machine
            max_phy_memory = self.physical.memory(physical_node) if self.physical.memory(
                physical_node) > max_phy_memory else max_phy_memory

        # LB, any feasible mapping requires at least this number of physical machines
        lower_bound = max(math.ceil(tot_req_cores / max_phy_cores), math.ceil(tot_req_memory / max_phy_memory))

        for n_partitions in range(lower_bound, len(compute_nodes) + 1):

            # partitioning of logical nodes in n_partitions partitions
            k_partition = get_partitions(self.logical.g, n_partitions=n_partitions)
            # random subset of hosts of size n_partitions
            phy_subset = random.sample(compute_nodes, k=n_partitions)

            # check if the partitioning is feasible
            try:
                #
                # logical nodes to physical nodes assignment
                #
                res_node_mapping = {}
                cores_used = defaultdict(int)
                memory_used = defaultdict(int)

                # iterate over each pair (physical_node i, logical nodes assigned to i)
                for physical_node, logical_nodes_assigned in zip(phy_subset, k_partition):
                    # check if node resources are not exceeded:
                    for logical_node in logical_nodes_assigned:
                        # cpu cores
                        cores_used[physical_node] += self.logical.req_cores(logical_node)
                        if self.physical.cores(physical_node) < cores_used[physical_node]:
                            raise NodeResourceError(physical_node, "cpu cores")
                        # memory
                        memory_used[physical_node] += self.logical.req_memory(logical_node)
                        if self.physical.memory(physical_node) < memory_used[physical_node]:
                            raise NodeResourceError(physical_node, "memory")
                        # assign the logical nodes to a physical node
                        res_node_mapping[logical_node] = physical_node

                #
                # logical links to physical links assignment
                #
                res_link_mapping = {}
                rate_used = defaultdict(int)

                # iterate over each logical link
                for (u, v) in self.logical.edges():
                    phy_u, phy_v = res_node_mapping[u], res_node_mapping[v]

                    # if u and v have been placed on the same physical machine go next
                    if phy_u == phy_v:
                        continue
                    # else, for each link in the physical path
                    for (i, j) in self.physical.find_path(phy_u, phy_v):

                        # get an interface with enough available rate
                        chosen_interface = next((interface for interface in self.physical.nw_interfaces(i, j) if
                                                 self.physical.rate(i, j, interface) - rate_used[
                                                     (i, j, interface)] >= self.logical.req_rate(u, v)), None)

                        # if such an interface does not exist raise an Exception
                        if not chosen_interface:
                            raise LinkCapacityError((i, j))
                        # else update the rate
                        rate_used[(i, j, chosen_interface)] += self.logical.req_rate(u, v)

                        if i == phy_u or j == phy_u:
                            source = (i, chosen_interface, j) if i == phy_u else (j, chosen_interface, i)
                        elif i == phy_v or j == phy_v:
                            dest = (i, chosen_interface, j) if i == phy_v else (j, chosen_interface, i)

                    res_link_mapping[(u, v)] = [(source + dest + (1,))]

                if self.physical.grouped_interfaces:
                    solution = Solution.map_to_multiple_interfaces(self.logical, self.physical, res_node_mapping,
                                                                   res_link_mapping)
                else:
                    solution = Solution(self.logical, self.physical, res_node_mapping, res_link_mapping)

                return n_partitions, solution

            except (NodeResourceError, LinkCapacityError, InfeasibleError):
                # unfeasible, increase the number of partitions to be used
                pass
        else:
            raise InfeasibleError
