import random
from collections import defaultdict

from networkx.algorithms.community.kernighan_lin import kernighan_lin_bisection

from mapping.constants import *
from mapping.embedding.solution import Solution
from mapping.embedding import EmbeddingSolver
from mapping.utils import timeit

class GetPartitions(object):
    """Callable object."""

    def __init__(self):
        # to keep track of the already computed partitions
        self._cache = {}

    def __call__(self, g, n_partitions):
        """Given the graph G and the number of partitions k, returns a list with k sets of nodes."""

        def _iterative_cutting(g, p):
            """helper function (iterative version)"""

            to_be_processed = [g]
            K = len(g.nodes()) / p

            res = []
            while len(to_be_processed) > 0:

                g = to_be_processed.pop()
                g_l, g_r = kernighan_lin_bisection(g, weight='rate')

                for partition in g_l, g_r:
                    if len(partition) > K:
                        to_be_processed.append(g.subgraph(partition))
                    else:
                        res.append(partition)
            return res

        def _recursive_cutting(g, p, res=[]):
            """helper function (recursive version)"""
            k = len(g.nodes()) / p

            g_l, g_r = kernighan_lin_bisection(g, weight='rate')

            for partition in g_l, g_r:
                if len(partition) > k:
                    _recursive_cutting(g.subgraph(partition), p / 2, res)
                else:
                    res.append(partition)

            return res

        # when computing a partitioning for the graph nodes,
        # if result is known for a smaller value of n_partitions
        # don't restart from scratch but use it as an initial value
        if g not in self._cache or len(self._cache[g]) < n_partitions:
            self._cache.clear()
            partitions = _recursive_cutting(g, p=n_partitions)
            self._cache[g] = partitions[:]
        else:
            partitions = self._cache[g][:]

        # merge small partitions to return the required number of partitions
        while len(partitions) > n_partitions:
            partitions.sort(key=len, reverse=True)
            e1 = partitions.pop()
            e2 = partitions.pop()
            partitions.append(e1.union(e2))
        return partitions


get_partitions = GetPartitions()


class EmbedBalanced(EmbeddingSolver):

    @timeit
    def solve(self, **kwargs):
        """Heuristic based on computing a k-balanced partitions of virtual nodes for then mapping the partition
           on a subset of the physical nodes.
        """

        compute_nodes = self.physical.compute_nodes

        for n_partitions_to_try in range(self._get_lb(), len(compute_nodes) + 1):
            # partitioning of virtual nodes in n_partitions_to_try partitions
            k_partition = get_partitions(self.virtual.g, n_partitions=n_partitions_to_try)
            # random subset of hosts of size n_partitions_to_try
            chosen_physical = random.sample(compute_nodes, k=n_partitions_to_try)

            #
            # check if the partitioning is a feasible solution
            #
            try:
                # virtual nodes to physical nodes assignment
                res_node_mapping = {}

                # iterate over each pair (physical_node i, virtual nodes assigned to i)
                for physical_node, assigned_virtual_nodes in zip(chosen_physical, k_partition):
                    # keep track of the node physical resources used
                    cores_used = memory_used = 0
                    # check if node resources are not exceeded:
                    for virtual_node in assigned_virtual_nodes:
                        # cpu cores
                        cores_used += self.virtual.req_cores(virtual_node)
                        if self.physical.cores(physical_node) < cores_used:
                            raise NodeResourceError(physical_node, "cpu cores")
                        # memory
                        memory_used += self.virtual.req_memory(virtual_node)
                        if self.physical.memory(physical_node) < memory_used:
                            raise NodeResourceError(physical_node, "memory")
                        # assign the virtual nodes to a physical node
                        res_node_mapping[virtual_node] = physical_node

                #
                # virtual links to physical links assignment
                #
                res_link_mapping = {}
                rate_used = defaultdict(int)

                # iterate over each virtual link between two virtual nodes not mapped on the same physical machine
                for (u, v) in ((u, v) for (u, v) in self.virtual.sorted_edges() if
                               res_node_mapping[u] != res_node_mapping[v]):

                    res_link_mapping[(u, v)] = []

                    # physical nodes on which u and v have been placed
                    phy_u, phy_v = res_node_mapping[u], res_node_mapping[v]

                    next_node = phy_u
                    # for each link in the physical path
                    for (i, j) in self.physical.find_path(phy_u, phy_v):

                        # get an interface_name with enough available rate
                        chosen_interface_id = next((interface for interface in self.physical.interfaces_ids(i, j) if
                                                    self.physical.rate(i, j, interface) - rate_used[(i, j, interface)] >=
                                                    self.virtual.req_rate(u, v)), None)

                        # if such an interface_name does not exist raise an Exception
                        if not chosen_interface_id:
                            raise LinkCapacityError(f"Capacity exceeded on ({i},{j})")

                        # else update the rate
                        rate_used[(i, j, chosen_interface_id)] += self.virtual.req_rate(u, v)

                        res_link_mapping[(u, v)].append(
                            (i, chosen_interface_id, j) if i == next_node else (j, chosen_interface_id, i))
                        next_node = j if i == next_node else i

                # build solution from the output
                self.solution = Solution.build_solution(self.virtual, self.physical, res_node_mapping, res_link_mapping)
                self.status = Solved
                return Solved

            except (NodeResourceError, LinkCapacityError):
                # unfeasible, increase the number of partitions to be used
                pass
        else:
            self.status = Infeasible
            return Infeasible



if __name__ == "__main__":
    from mapping.embedding import PhysicalNetwork
    from mapping.virtual import VirtualNetwork

    physical_topo = PhysicalNetwork.grid5000("grisou", group_interfaces=True)
    virtual_topo = VirtualNetwork.create_random_nw(n_nodes=66)
    # virtual_topo = VirtualNetwork.create_fat_tree(k=4)

    embed = EmbedBalanced(virtual_topo, physical_topo)
    time_solution = embed.solve()
    print(time_solution, embed.status)
    print(embed.solution)