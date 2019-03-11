import random
from collections import defaultdict

from mapping.constants import *
from mapping.embedding import EmbeddingSolver
from mapping.embedding.solution import Solution
from mapping.utils import timeit


class RandomSelection(EmbeddingSolver):

    @timeit
    def solve(self, **kwargs):
        seed = kwargs.get("seed", 66)
        my_random = random.Random(seed)

        compute_nodes = sorted(list(self.physical.compute_nodes))

        while True:
            res_node_mapping = {}
            cores_used = defaultdict(int)
            memory_used = defaultdict(int)

            # random virtual node to physical node assignment
            for virtual_node in self.virtual.nodes():
                chosen_phy = my_random.choice(compute_nodes)

                res_node_mapping[virtual_node] = chosen_phy
                cores_used[chosen_phy] += self.virtual.req_cores(virtual_node)
                memory_used[chosen_phy] += self.virtual.req_memory(virtual_node)

                if cores_used[chosen_phy] > self.physical.cores(chosen_phy) or memory_used[
                    chosen_phy] > self.physical.memory(chosen_phy):
                    continue

            res_link_mapping = {}
            rate_used = defaultdict(int)
            # link mapping
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
                    feasible_interfaces_ids = [interface_id for interface_id in self.physical.interfaces_ids(i, j)
                                               if self.physical.rate(i, j, interface_id) - rate_used[
                                                   (i, j, interface_id)] >= self.virtual.req_rate(u, v)]

                    if feasible_interfaces_ids is None:
                        continue
                    else:
                        chosen_interface_id = my_random.choice(feasible_interfaces_ids)

                    # else update the rate
                    rate_used[(i, j, chosen_interface_id)] += self.virtual.req_rate(u, v)

                    res_link_mapping[(u, v)].append(
                        (i, chosen_interface_id, j) if i == next_node else (j, chosen_interface_id, i))
                    next_node = j if i == next_node else i

            # build solution from the output
            self.solution = Solution.build_solution(self.virtual, self.physical, res_node_mapping, res_link_mapping)
            self.status = Solved
            return Solved


if __name__ == "__main__":
    from mapping.embedding import PhysicalNetwork
    from mapping.virtual import VirtualNetwork

    physical_topo = PhysicalNetwork.from_files("grisou", group_interfaces=False)
    virtual_topo = VirtualNetwork.create_random_nw(n_nodes=66)
    # virtual_topo = VirtualNetwork.create_fat_tree(k=4)

    prob = RandomSelection(virtual_topo, physical_topo)
    time_solution = prob.solve(seed=1)
    print(time_solution, prob.status)
    print(prob.solution)
    for (u, v) in virtual_topo.edges():
        print(f"*** virtual link {(u, v)} mapped on")
        if prob.solution.node_info(u) != prob.solution.node_info(v):
            print("LINK MAP")
            for link_map in prob.solution.link_info((u, v)):
                print(link_map)
            print("PATH")
            for path in prob.solution.path_info((u, v)):
                print(path)
            print("")
        else:
            print("Nodes are on the same physical machine")
