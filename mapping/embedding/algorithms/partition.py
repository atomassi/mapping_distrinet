import random
from collections import defaultdict

from mapping.constants import *
from mapping.embedding.solution import Solution
from mapping.embedding import EmbeddingSolver
from mapping.utils import timeit


def get_partitions(virtual, n_partitions, n_swaps=100):
    """ Divide the nodes in n_partitions bins and then tries to swap nodes to reduce the cut weight."""

    nodes = list(virtual.nodes())
    random.shuffle(nodes)
    # node -> id of the partition in which it is contained
    nodes_partition = {node: id_node % n_partitions for id_node, node in enumerate(nodes)}

    # current cost for the partition
    old_cost = sum(virtual.req_rate(u, v) for (u, v) in virtual.edges() if nodes_partition[u] != nodes_partition[v])

    for _ in range(n_swaps):
        # take two random nodes
        u1, u2 = random.sample(nodes, k=2)
        # if the partitions ids of u1 and u2 are the same continue
        if nodes_partition[u1] == nodes_partition[u2]:
            continue
        # store the old partition ids of u1 and u2
        old_u1, old_u2 = nodes_partition[u1], nodes_partition[u2]
        # swap the partitions
        nodes_partition[u1], nodes_partition[u2] = nodes_partition[u2], nodes_partition[u1]
        # compute the new cost
        new_cost = sum(virtual.req_rate(u, v) for (u, v) in virtual.edges() if nodes_partition[u] != nodes_partition[v])

        if new_cost < old_cost:
            # update the current cost
            old_cost = new_cost
        else:
            # go back to the previous solution
            nodes_partition[u1], nodes_partition[u2] = old_u1, old_u2

    partitions = defaultdict(list)
    for node, id_partition in nodes_partition.items():
        partitions[id_partition].append(node)
    return partitions.values()


class EmbedPartition(EmbeddingSolver):

    @timeit
    def solve(self, **kwargs):
        """Heuristic based on computing a k-balanced partitions of virtual nodes for then mapping the partition
           on a subset of the physical nodes.
        """

        for n_partitions_to_try in range(self._get_lb(), len(self.physical.compute_nodes) + 1):
            # partitioning of virtual nodes in n_partitions_to_try partitions
            k_partition = get_partitions(self.virtual, n_partitions=n_partitions_to_try)
            # random subset of hosts of size n_partitions_to_try
            chosen_physical = random.sample(self.physical.compute_nodes, k=n_partitions_to_try)

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
                                                    self.physical.rate(i, j, interface) - rate_used[
                                                     (i, j, interface)] >= self.virtual.req_rate(u, v)), None)
                        # if such an interface_name does not exist raise an Exception
                        if chosen_interface_id is None:
                            raise LinkCapacityError(f"Capacity exceeded on ({i},{j})")
                        # else update the rate
                        rate_used[(i, j, chosen_interface_id)] += self.virtual.req_rate(u, v)

                        res_link_mapping[(u, v)].append(
                            (i, chosen_interface_id, j) if i == next_node else (j, chosen_interface_id, i))
                        next_node = j if i == next_node else i

                # build solution from the output
                self.solution =  Solution.build_solution(self.virtual, self.physical, res_node_mapping, res_link_mapping)
                self.status = Solved
                return Solved

            except (NodeResourceError, LinkCapacityError) as err:
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

    embed = EmbedPartition(virtual_topo, physical_topo)
    time_solution = embed.solve()
    print(time_solution, embed.status)
    print(embed.solution)