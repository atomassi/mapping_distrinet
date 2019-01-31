import math
import random
from collections import defaultdict

from networkx.algorithms.community.kernighan_lin import kernighan_lin_bisection

from embedding.exceptions import NodeResourceError, LinkCapacityError, InfeasibleError
from embedding.solve import Embed
from .solution import Solution


class GetPartition(object):
    """callable object
    """

    def __init__(self):
        # to keep track of the already computed partitions
        self._memo = {}

    def __call__(self, g, n_partitions):
        """Given the graph G and the number of partitions k,
           returns a list with k sets of nodes
        """

        def iterative_cutting(g, k, restart_from=None):
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
                else:
                    for partition in kernighan_lin_bisection(g.subgraph(p0), weight='rate'):
                        if len(partition) > k:
                            to_be_processed.append(g.subgraph(partition))
                        else:
                            partitions.append(partition)

            return partitions

        k = len(g.nodes()) / n_partitions

        # when computing a partitioning for the graph nodes,
        # if result is known for a smaller value of n_partitions
        # don't restart from scratch but use it as an initial value
        if g not in self._memo:
            self._memo.clear()
        partitions = iterative_cutting(g, k, self._memo.get(g, None))
        self._memo[g] = partitions

        # merge small partitions to return the required number of partitions
        if len(partitions) > n_partitions:
            while len(partitions) > n_partitions:
                partitions.sort(key=len)
                e1 = partitions.pop(0)
                e2 = partitions.pop(0)
                partitions.append(e1.union(e2))
        return partitions


get_partitions = GetPartition()


class EmbedHeu(Embed):

    def get_LB(self):
        """Return a lower bound on the minimum number of physical machines needed to map all the virtual nodes
        """

        # nodes able to host VMs
        compute_nodes = self.physical.compute_nodes

        tot_req_cores = tot_req_memory = 0
        for virtual_node in self.virtual.nodes():
            # the total number of cores to be mapped
            tot_req_cores += self.virtual.req_cores(virtual_node)
            # the total required memory to be mapped
            tot_req_memory += self.virtual.req_memory(virtual_node)

        max_phy_memory = max_phy_cores = 0
        for physical_node in compute_nodes:
            # the maximum capacity in terms of cores for a physical machine
            max_phy_cores = self.physical.cores(physical_node) if self.physical.cores(
                physical_node) > max_phy_cores else max_phy_cores
            # the maximum capacity in terms of memory for a physical machine
            max_phy_memory = self.physical.memory(physical_node) if self.physical.memory(
                physical_node) > max_phy_memory else max_phy_memory

        # lower bound, any feasible mapping requires at least this number of physical machines
        return max(math.ceil(tot_req_cores / max_phy_cores), math.ceil(tot_req_memory / max_phy_memory))

    @Embed.timeit
    def __call__(self, *args, **kwargs):
        """Heuristic based on computing a k-balanced partitions of virtual nodes for then mapping the partition
           on a subset of the physical nodes.
        """

        compute_nodes = self.physical.compute_nodes

        for n_partitions_to_try in range(self.get_LB(), len(compute_nodes) + 1):

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

                # to keep track of the paths between 2 physical nodes
                computed_paths = {}

                # iterate over each virtual link between two virtual nodes not mapped on the same physical machine
                for (u, v) in ((u, v) for (u, v) in self.virtual.edges() if res_node_mapping[u] != res_node_mapping[v]):

                    # physical nodes on which u and v have been placed
                    phy_u, phy_v = res_node_mapping[u], res_node_mapping[v]

                    # if a physical path between phy_u and phy_v has not been computed yet
                    # check if a path between phy_v and phy_u has been computed and reverse it
                    # otherwise compute it and store it
                    if (phy_u, phy_v) not in computed_paths:
                        if (phy_v, phy_u) in computed_paths:
                            computed_paths[(phy_u, phy_v)] = list(reversed(computed_paths[(phy_v, phy_u)]))
                        else:
                            computed_paths[(phy_u, phy_v)] = list(self.physical.find_path(phy_u, phy_v))

                    # for each link in the physical path
                    for (i, j) in computed_paths[(phy_u, phy_v)]:
                        # get an interface with enough available rate
                        chosen_interface = next((interface for interface in self.physical.nw_interfaces(i, j) if
                                                 self.physical.rate(i, j, interface) - rate_used[
                                                     (i, j, interface)] >= self.virtual.req_rate(u, v)), None)
                        # if such an interface does not exist raise an Exception
                        if not chosen_interface:
                            raise LinkCapacityError((i, j))
                        # else update the rate
                        rate_used[(i, j, chosen_interface)] += self.virtual.req_rate(u, v)

                        # get physical source and destination nodes and interfaces for the virtual link
                        if i == phy_u or j == phy_u:
                            source = (i, chosen_interface, j) if i == phy_u else (j, chosen_interface, i)
                        elif i == phy_v or j == phy_v:
                            dest = (i, chosen_interface, j) if i == phy_v else (j, chosen_interface, i)

                    # update the result
                    res_link_mapping[(u, v)] = [(source + dest + (1,))]

                # if interfaces have been grouped into a single one, ungroup them
                if self.physical.grouped_interfaces:
                    solution = Solution.map_to_multiple_interfaces(self.virtual, self.physical, res_node_mapping,
                                                                   res_link_mapping)
                else:
                    solution = Solution(self.virtual, self.physical, res_node_mapping, res_link_mapping)

                # return the number of partitions used and the solution found
                return n_partitions_to_try, solution

            except (NodeResourceError, LinkCapacityError):
                # unfeasible, increase the number of partitions to be used
                pass
        else:
            raise InfeasibleError
