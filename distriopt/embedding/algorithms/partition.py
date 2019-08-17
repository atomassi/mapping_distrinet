import logging
import random
from collections import defaultdict

from distriopt.constants import *
from distriopt.decorators import timeit
from distriopt.embedding import EmbedSolver
from distriopt.embedding.solution import Solution

_log = logging.getLogger(__name__)


def get_partitions(virtual, n_partitions, n_swaps=100):
    """ Divide the nodes in n_partitions bins and then tries to swap nodes to reduce the cut weight."""

    nodes = list(virtual.nodes())
    random.shuffle(nodes)
    # node -> id of the partition in which it is contained
    nodes_partition = {
        node: id_node % n_partitions for id_node, node in enumerate(nodes)
    }

    # current cost for the partition
    old_cost = sum(
        virtual.req_rate(u, v)
        for (u, v) in virtual.edges()
        if nodes_partition[u] != nodes_partition[v]
    )

    for _ in range(n_swaps):
        # take two random nodes
        u1, u2 = random.sample(nodes, k=2)
        # if the partitions ids of u1 and u2 are the same continue
        if nodes_partition[u1] == nodes_partition[u2]:
            continue
        # store the old partition ids of u1 and u2
        old_u1, old_u2 = nodes_partition[u1], nodes_partition[u2]
        # swap the partitions
        nodes_partition[u1], nodes_partition[u2] = (
            nodes_partition[u2],
            nodes_partition[u1],
        )
        # compute the new cost
        new_cost = sum(
            virtual.req_rate(u, v)
            for (u, v) in virtual.edges()
            if nodes_partition[u] != nodes_partition[v]
        )

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


class EmbedPartition(EmbedSolver):
    @timeit
    def solve(self, **kwargs):
        """Heuristic based on computing a k-balanced partitions of virtual nodes for then mapping the partition
           on a subset of the physical nodes.
        """
        sorted_compute_nodes = sorted(
            self.physical.compute_nodes,
            key=lambda x: self.physical.cores(x) * 1000 + self.physical.memory(x),
            reverse=True,
        )

        for n_partitions_to_try in range(
            self.lower_bound(), len(self.physical.compute_nodes) + 1
        ):
            # partitioning of virtual nodes in n_partitions_to_try partitions
            k_partition = get_partitions(self.virtual, n_partitions=n_partitions_to_try)
            # random subset of hosts of size n_partitions_to_try
            chosen_physical = sorted_compute_nodes[:n_partitions_to_try]
            #
            # check if the partitioning is a feasible solution
            #
            try:
                # virtual nodes to physical nodes assignment
                res_node_mapping = {}

                # iterate over each pair (physical_node i, virtual nodes assigned to i)
                for physical_node, assigned_virtual_nodes in zip(
                    chosen_physical, k_partition
                ):
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
                for (u, v) in (
                    (u, v)
                    for (u, v) in self.virtual.sorted_edges()
                    if res_node_mapping[u] != res_node_mapping[v]
                ):

                    res_link_mapping[(u, v)] = []

                    # physical nodes on which u and v have been placed
                    phy_u, phy_v = res_node_mapping[u], res_node_mapping[v]

                    # for each link in the physical path
                    for (i, j, device_id) in self.physical.find_path(
                        phy_u,
                        phy_v,
                        req_rate=self.virtual.req_rate(u, v),
                        used_rate=rate_used,
                    ):
                        rate_used[(i, j, device_id)] += self.virtual.req_rate(u, v)
                        res_link_mapping[(u, v)].append((i, device_id, j))

                # build solution from the output
                self.solution = Solution.build_solution(
                    self.virtual, self.physical, res_node_mapping, res_link_mapping
                )
                self.status = Solved
                return Solved

            except (NodeResourceError, NoPathFoundError) as err:
                # unfeasible, increase the number of partitions to be used
                pass
        else:
            self.status = Infeasible
            return Infeasible


if __name__ == "__main__":
    from distriopt.embedding import PhysicalNetwork
    from distriopt import VirtualNetwork

    import networkx as nx

    g = nx.Graph()
    g.add_node("Node_0", cores=3, memory=3000)
    g.add_node("Node_1", cores=3, memory=3000)
    g.add_edge("Node_0", "Node_1", rate=20000)

    virtual_topo = VirtualNetwork(g)

    # unfeasible, not enough rate
    physical_topo = PhysicalNetwork.create_test_nw(
        cores=4, memory=4000, rate=10000, group_interfaces=False
    )

    prob = EmbedPartition(virtual_topo, physical_topo)
    time_solution, status = prob.solve()
    print(status)

    exit(1)

    physical_topo = PhysicalNetwork.from_files("grisou", group_interfaces=False)
    virtual_topo = VirtualNetwork.create_random_nw(n_nodes=66)
    # virtual_topo = VirtualNetwork.create_fat_tree(k=4)

    embed = EmbedPartition(virtual_topo, physical_topo)
    time_solution = embed.solve()
    print(time_solution, embed.status)
    print(embed.solution)
