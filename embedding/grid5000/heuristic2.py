import random
from collections import defaultdict

from embedding.exceptions import NodeResourceError, LinkCapacityError, InfeasibleError
from embedding.grid5000.solution import Solution
from embedding.solve import Embed
from embedding.utils import timeit


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


class EmbedHeu(Embed):

    @timeit
    def __call__(self, *args, **kwargs):
        """Heuristic based on computing a k-balanced partitions of virtual nodes for then mapping the partition
           on a subset of the physical nodes.
        """

        compute_nodes = self.physical.compute_nodes

        for n_partitions_to_try in range(self._get_LB(), len(compute_nodes) + 1):
            # partitioning of virtual nodes in n_partitions_to_try partitions
            k_partition = get_partitions(self.virtual, n_partitions=n_partitions_to_try)
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

            except (NodeResourceError, LinkCapacityError) as err:
                # unfeasible, increase the number of partitions to be used
                pass
        else:
            raise InfeasibleError


if __name__ == "__main__":
    from embedding.grid5000 import PhysicalNetwork
    from embedding.virtual import VirtualNetwork

    physical_topo = PhysicalNetwork.grid5000("grisou", group_interfaces=False)
    # virtual_topo = VirtualNetwork.create_random_nw(n_nodes=80)
    virtual_topo = VirtualNetwork.create_fat_tree(k=12)

    time_solution, (value_solution, solution) = EmbedHeu(virtual_topo, physical_topo)()
    print(time_solution, value_solution)
    solution.verify_solution()
