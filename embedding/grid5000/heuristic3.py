import itertools
from collections import defaultdict, Counter, deque

from embedding.constants import *
from embedding.grid5000.solution import Solution
from embedding.solve import Embed
from embedding.utils import timeit


class EmbedHeu(Embed):

    @timeit
    def place(self, **kwargs):
        """2 phases:
           - first assign virtual nodes to physical nodes
           - if link rate is exceeded, move virtual nodes until links are not saturated anymore
        """

        selected, not_selected = deque(), set(self.physical.compute_nodes)
        used_resources = {'cores': defaultdict(int), 'memory': defaultdict(int)}

        #
        # place virtual nodes and give priority to already selected nodes
        #
        res_node_mapping = {}
        for virtual_node in self.virtual.nodes():

            # required cores and memory
            req_cores, req_memory = self.virtual.req_cores(virtual_node), self.virtual.req_memory(virtual_node)

            # for each physical node, giving priority to the already selected ones
            for phy_node in itertools.chain(selected, not_selected):
                # if resources are enough
                if used_resources['cores'][phy_node] + req_cores <= self.physical.cores(phy_node) and \
                        used_resources['memory'][phy_node] + req_memory <= self.physical.memory(phy_node):

                    # assign phy node to virtual_node
                    res_node_mapping[virtual_node] = phy_node

                    # update selected and not_selected sets
                    try:
                        not_selected.remove(phy_node)
                        selected.appendleft(phy_node)
                    except KeyError:
                        pass

                    # update the resources used on the selected node
                    used_resources['cores'][phy_node] += req_cores
                    used_resources['memory'][phy_node] += req_memory
                    break
            else:
                # this means that resources on physical nodes are not enough
                raise InfeasibleError

        #
        # compute the paths given the virtual nodes to physical nodes assignment
        #
        rate_used = defaultdict(int)
        use_link = defaultdict(set)
        res_link_mapping = defaultdict(list)
        # iterate over each virtual link between two virtual nodes not mapped on the same physical machine
        for (u, v) in ((u, v) for (u, v) in self.virtual.sorted_edges() if res_node_mapping[u] != res_node_mapping[v]):

            # physical nodes on which u and v have been placed
            phy_u, phy_v = res_node_mapping[u], res_node_mapping[v]

            # find the physical path
            next_node = phy_u
            for (i, j) in self.physical.find_path(phy_u, phy_v):
                # get the interface with the maximum available rate
                chosen_interface = max((interface for interface in self.physical.nw_interfaces(i, j)),
                                       key=lambda interface: self.physical.rate(i, j, interface) - rate_used[
                                           (i, j, interface)])

                # update the rate used
                rate_used[(i, j, chosen_interface)] += self.virtual.req_rate(u, v)
                # add the virtual link in the list of virtual links that the physical link
                use_link[(i, j, chosen_interface)].add((u, v))
                # add to the path
                res_link_mapping[(u, v)].append(
                    (i, chosen_interface, j) if i == next_node else (j, chosen_interface, i))
                # update the next node in the path
                next_node = j if i == next_node else i

        # move nodes until link rate is not anymore exceeded
        exceeded_rate = sum(
            max(0, rate_used[(i, j, interface)] - self.physical.rate(i, j, interface)) for (i, j, interface) in
            rate_used)

        # while all link contraints are not satisfied
        while exceeded_rate > 0:

            # take the violated links and the rate in excess on them
            violated_links = {(i, j, interface): rate_used[(i, j, interface)] - self.physical.rate(i, j, interface) for
                              (i, j, interface) in rate_used
                              if rate_used[(i, j, interface)] - self.physical.rate(i, j, interface) > 0}

            # take the link with the highest exceeded rate
            most_violated_link = max(violated_links, key=violated_links.get)

            # for each physical node (giving priority to the already selected ones)
            for node_to_move, phy_node in itertools.product(
                    (u for (u, freq) in Counter(itertools.chain(*use_link[most_violated_link])).most_common()),
                    itertools.chain(selected, not_selected)):

                # if resources are enough
                if phy_node != res_node_mapping[node_to_move] \
                        and used_resources['cores'][phy_node] + self.virtual.req_cores(
                    node_to_move) <= self.physical.cores(phy_node) and \
                        used_resources['memory'][phy_node] + self.virtual.req_memory(
                    node_to_move) <= self.physical.memory(phy_node):

                    # physical node to which it was previously assigned
                    prev_phy_node = res_node_mapping[node_to_move]

                    # assign virtual_node to the physical node
                    res_node_mapping[node_to_move] = phy_node

                    # temporary data structures to keep track of the changes wrt the current solution
                    diff_rate = defaultdict(int)
                    diff_vlinks = {'add': defaultdict(set), 'remove': defaultdict(set)}
                    new_link_mapping = defaultdict(list)

                    # for each virtual link adjacent to the virtual node which is being moved
                    for (u, v) in ((node_to_move, neighbor) if node_to_move < neighbor else (
                            neighbor, node_to_move) for neighbor in self.virtual.neighbors(node_to_move)
                                   if res_node_mapping[neighbor] != res_node_mapping[node_to_move]):
                        phy_u, phy_v = res_node_mapping[u], res_node_mapping[v]

                        # for each link in the previous path
                        for (i, interface, j) in res_link_mapping[(u, v)]:
                            if i < j:
                                diff_rate[(i, j, interface)] -= self.virtual.req_rate(u, v)
                                diff_vlinks['remove'][(i, j, interface)].add((u, v))
                            else:
                                diff_rate[(j, i, interface)] -= self.virtual.req_rate(u, v)
                                diff_vlinks['remove'][(j, i, interface)].add((u, v))

                        # for each link in the new physical path
                        next_node = phy_u
                        for (i, j) in self.physical.find_path(phy_u, phy_v):
                            # get the interface with the maximum available rate
                            chosen_interface = max((interface for interface in self.physical.nw_interfaces(i, j)),
                                                   key=lambda interface: self.physical.rate(i, j, interface) -
                                                                         rate_used[(i, j, interface)] -
                                                                         diff_rate[(i, j, interface)])

                            new_link_mapping[(u, v)].append(
                                (i, chosen_interface, j) if i == next_node else (j, chosen_interface, i))
                            next_node = j if i == next_node else i

                            diff_rate[(i, j, chosen_interface)] += self.virtual.req_rate(u, v)
                            diff_vlinks['add'][(i, j, chosen_interface)].add((u, v))

                    # compute the new exceeded rate after having moved the node
                    new_exceeded_rate = sum(
                        max(0, rate_used[(i, j, interface)] + diff_rate[(i, j, interface)] - self.physical.rate(i, j,
                                                                                                           interface))
                        for (i, j, interface) in rate_used)

                    # if the rate in exceed is decreased, update the partial results
                    if new_exceeded_rate < exceeded_rate:

                        exceeded_rate = new_exceeded_rate

                        if phy_node in not_selected:
                            not_selected.remove(phy_node)
                            selected.appendleft(phy_node)

                        # free resources on previous physical node
                        used_resources['cores'][prev_phy_node] -= self.virtual.req_cores(node_to_move)
                        used_resources['memory'][prev_phy_node] -= self.virtual.req_memory(node_to_move)

                        # add resources used on the new physical node
                        used_resources['cores'][phy_node] += self.virtual.req_cores(node_to_move)
                        used_resources['memory'][phy_node] += self.virtual.req_memory(node_to_move)

                        # update the rate used on the network interfaces
                        for (i, j, interface) in diff_rate:
                            rate_used[(i, j, interface)] += diff_rate[(i, j, interface)]

                        # update link usage
                        for (i, j, interface) in set(diff_vlinks['remove']) | set(diff_vlinks['add']):
                            use_link[(i, j, interface)] = use_link[(i, j, interface)] - (
                                diff_vlinks['remove'][(i, j, interface)]) | diff_vlinks['add'][(i, j, interface)]

                        # update the link mapping for the virtual links
                        for (u, v) in new_link_mapping:
                            res_link_mapping[(u, v)] = new_link_mapping[(u, v)]

                        break

            else:
                raise InfeasibleError

        self.solution = Solution.build_solution(self.virtual, self.physical, res_node_mapping, res_link_mapping)
        self.status = Solved
        return Solved



if __name__ == "__main__":
    from embedding.grid5000 import PhysicalNetwork
    from embedding.virtual import VirtualNetwork

    physical_topo = PhysicalNetwork.grid5000("grisou", group_interfaces=True)
    virtual_topo = VirtualNetwork.create_random_nw(n_nodes=66)
    # virtual_topo = VirtualNetwork.create_fat_tree(k=4)

    embed = EmbedHeu(virtual_topo, physical_topo)
    time_solution = embed.place()
    print(time_solution, embed.status)
    print(embed.solution)
