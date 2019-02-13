import itertools
from collections import defaultdict, Counter

from embedding.exceptions import InfeasibleError
from embedding.grid5000.solution import Solution
from embedding.solve import Embed


class EmbedHeu(Embed):

    @Embed.timeit
    def __call__(self, *args, **kwargs):
        """2 phases:
           - first assign virtual nodes to physical nodes
           - if link rate is exceeded, move virtual nodes until links are not saturated anymore
        """

        not_selected = set(self.physical.compute_nodes)
        selected = list()

        used_cores = defaultdict(int)
        used_memory = defaultdict(int)

        res_node_mapping = {}
        #
        # place virtual nodes and give priority to already selected nodes
        #
        for virtual_node in self.virtual.nodes():

            # required cores and memory
            req_cores, req_memory = self.virtual.req_cores(virtual_node), self.virtual.req_memory(virtual_node)

            # for each physical node, giving priority to the already selected ones
            for phy_node in itertools.chain(reversed(selected), not_selected):
                # if resources are enough
                if used_cores[phy_node] + req_cores <= self.physical.cores(phy_node) and \
                        used_memory[phy_node] + req_memory <= self.physical.memory(phy_node):

                    # assign phy node to virtual_node
                    res_node_mapping[virtual_node] = phy_node

                    # update selected and not_selected sets
                    try:
                        not_selected.remove(phy_node)
                        selected.append(phy_node)
                    except KeyError:
                        pass

                    # update the resources used on the selected node
                    used_cores[phy_node] += req_cores
                    used_memory[phy_node] += req_memory
                    break
            else:
                # this means that resources on physical nodes are not enough
                raise InfeasibleError

        #
        # compute the paths given the virtual nodes to physical nodes assignment
        #
        rate_used = defaultdict(int)
        use_link = defaultdict(set)
        link_mapping = defaultdict(list)

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
                # get the interface with the maximum available rate
                chosen_interface = max((interface for interface in self.physical.nw_interfaces(i, j)),
                                       key=lambda interface: self.physical.rate(i, j, interface) - rate_used[
                                           (i, j, interface)])

                # update the rate used
                rate_used[(i, j, chosen_interface)] += self.virtual.req_rate(u, v)
                # add the virtual link in the list of virtual links that the physical link
                use_link[(i, j, chosen_interface)].add((u, v))
                # path
                link_mapping[(u, v)].append((i, j, chosen_interface))

        # move nodes until link rate is not exceeded
        exceeded_rate = sum(
            max(0, rate_used[(i, j, interface)] - self.physical.rate(i, j, interface)) for (i, j, interface) in
            rate_used)

        while exceeded_rate > 0:

            # take the violated links and the rate in excess on them
            violated_links = {(i, j, interface): rate_used[(i, j, interface)] - self.physical.rate(i, j, interface) for
                              (i, j, interface) in rate_used if
                              rate_used[(i, j, interface)] - self.physical.rate(i, j, interface) > 0}

            # take the link with the highest exceeded rate
            most_violated_link = max(violated_links, key=violated_links.get)

            # for each physical node (giving priority to the already selected ones)
            for node_to_move, phy_node in itertools.product(
                    (u for (u, freq) in Counter(itertools.chain(*use_link[most_violated_link])).most_common()),
                    itertools.chain(reversed(selected), not_selected)):

                # if resources are enough
                if phy_node != res_node_mapping[node_to_move] \
                        and used_cores[phy_node] + self.virtual.req_cores(node_to_move) <= self.physical.cores(phy_node) and \
                        used_memory[phy_node] + self.virtual.req_memory(node_to_move) <= self.physical.memory(phy_node):

                    # physical node to which it was assigned
                    prev_phy_node = res_node_mapping[node_to_move]

                    # assign phy node to virtual_node
                    res_node_mapping[node_to_move] = phy_node

                    # temporary data structures to keep track of the changes wrt the current solution
                    diff_rate = defaultdict(int)
                    diff_vlinks_add = defaultdict(set)
                    diff_vlinks_remove = defaultdict(set)
                    new_link_mapping = defaultdict(list)

                    # for each virtual link adjacent to the virtual node which is being moved
                    for (u, v) in ((node_to_move, neighbor) if node_to_move < neighbor else (
                            neighbor, node_to_move) for neighbor in self.virtual.neighbors(node_to_move)
                                   if res_node_mapping[neighbor] != res_node_mapping[node_to_move]):
                        phy_u, phy_v = res_node_mapping[u], res_node_mapping[v]

                        for (i, j, interface) in link_mapping[(u, v)]:
                            diff_rate[(i, j, interface)] -= self.virtual.req_rate(u, v)
                            diff_vlinks_remove[(i, j, interface)].add((u, v))

                        if (phy_u, phy_v) not in computed_paths:
                            if (phy_v, phy_u) in computed_paths:
                                computed_paths[(phy_u, phy_v)] = list(reversed(computed_paths[(phy_v, phy_u)]))
                            else:
                                computed_paths[(phy_u, phy_v)] = list(self.physical.find_path(phy_u, phy_v))

                        # for each link in the physical path
                        for (i, j) in computed_paths[(phy_u, phy_v)]:
                            # get the interface with the maximum available rate
                            chosen_interface = max((interface for interface in self.physical.nw_interfaces(i, j)),
                                                   key=lambda interface: self.physical.rate(i, j, interface) -
                                                                         rate_used[(i, j, interface)] -
                                                                         diff_rate[(i, j, interface)])

                            new_link_mapping[(u, v)].append((i, j, chosen_interface))
                            diff_rate[(i, j, chosen_interface)] += self.virtual.req_rate(u, v)
                            diff_vlinks_add[(i, j, chosen_interface)].add((u, v))

                    new_exceeded_rate = sum(
                        max(0, rate_used[(i, j, interface)] + diff_rate[(i, j, interface)] - self.physical.rate(i, j, interface))
                        for (i, j, interface) in rate_used)

                    if new_exceeded_rate < exceeded_rate:
                        exceeded_rate = new_exceeded_rate

                        try:
                            not_selected.remove(phy_node)
                            selected.append(phy_node)
                        except KeyError:
                            pass

                        # free resources on previous physical node
                        used_cores[prev_phy_node] -= self.virtual.req_cores(node_to_move)
                        used_memory[prev_phy_node] -= self.virtual.req_memory(node_to_move)

                        # add resources used on the new physical node
                        used_cores[phy_node] += self.virtual.req_cores(node_to_move)
                        used_memory[phy_node] += self.virtual.req_memory(node_to_move)

                        # update the rate used on the network interfaces
                        for (i, j, interface) in diff_rate:
                            rate_used[(i, j, interface)] += diff_rate[(i, j, interface)]

                        # update link usage
                        for (i, j, interface) in set(diff_vlinks_remove) | set(diff_vlinks_add):
                            use_link[(i, j, interface)] = use_link[(i, j, interface)] - (
                            diff_vlinks_remove[(i, j, interface)]) | diff_vlinks_add[(i, j, interface)]

                        # update the link mapping for the virtual links
                        for (u, v) in new_link_mapping:
                            link_mapping[(u, v)] = new_link_mapping[(u, v)]

                        break

            else:
                raise InfeasibleError

        res_link_mapping = defaultdict(list)

        for (u, v) in ((u, v) for (u, v) in self.virtual.edges() if res_node_mapping[u] != res_node_mapping[v]):

            phy_u, phy_v = res_node_mapping[u], res_node_mapping[v]

            for (i, j, interface) in link_mapping[(u, v)]:
                if i == phy_u or j == phy_u:
                    source = (i, interface, j) if i == phy_u else (j, interface, i)
                elif i == phy_v or j == phy_v:
                    dest = (i, interface, j) if i == phy_v else (j, interface, i)

            res_link_mapping[(u, v)] = [(source + dest + (1,))]

        if self.physical.grouped_interfaces:
            solution = Solution.map_to_multiple_interfaces(self.virtual, self.physical, res_node_mapping,
                                                           res_link_mapping)
        else:
            solution = Solution(self.virtual, self.physical, res_node_mapping, res_link_mapping)

        return len(selected), solution


if __name__ == "__main__":
    from embedding.grid5000 import PhysicalNetwork
    from embedding.virtual import VirtualNetwork

    physical_topo = PhysicalNetwork.grid5000("grisou", group_interfaces=False)
    virtual_topo = VirtualNetwork.create_random_nw(n_nodes=170)
    # virtual_topo = VirtualNetwork.create_fat_tree(k=12)

    time_solution, (value_solution, solution) = EmbedHeu(virtual_topo, physical_topo)()
    print(time_solution, value_solution)
    solution.verify_solution()
