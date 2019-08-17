import logging
from collections import defaultdict, Counter, deque

import numpy as np
from networkx.algorithms.community.kernighan_lin import kernighan_lin_bisection

from distriopt.constants import *
from distriopt.decorators import timeit
from distriopt.embedding import EmbedSolver
from distriopt.embedding.solution import Solution

_log = logging.getLogger(__name__)


class Node(object):
    """Model a Node.

    Each node represents a partition.
    The left and right child, if not None, partition the nodes into 2 sets.
    Each node also contains a reference to the father.
    """

    def __init__(self, partition, cores=0, memory=0, parent=None):
        self.parent = parent
        self.partition = partition
        self.cores = cores
        self.memory = memory
        self.l = None
        self.r = None


class Tree(object):
    """Represent a partitions tree. Each node is an instance of the Node class."""

    def __init__(self, root):
        self.root = root
        self.placed = set([])

    def print_tree(self):
        """Perform a BFS visit and print the tree."""
        to_visit = deque([(self.root, 0)])

        while to_visit:
            (current, level) = to_visit.popleft()
            print(current.partition, level)
            if current.l:
                to_visit.append((current.l, level + 1))
            if current.r:
                to_visit.append((current.r, level + 1))

    def bfs_visit(self):
        """Perform a BFS visit of the partitions tree ignoring the already placed partitions."""

        self.placed = set([])
        to_visit = deque()

        if self.root:
            to_visit.append(self.root)

        while to_visit:
            current = to_visit.popleft()
            if not current.partition.issubset(self.placed):
                yield current
                if current.l:
                    to_visit.append(current.l)
                if current.r:
                    to_visit.append(current.r)


def partition(virtual, algo="min_cut"):
    """Iterative min cut algorithm.

    Iteratively partitions the graph according to the chosen algorithm (either min cut or min bisection)
    until the size of the partition is under a certain threshold.
    """

    class UnionFind:
        """Utility Class used by the MinCut algorithm."""

        def __init__(self, nodes):
            self.parents = {u: u for u in nodes}
            self.ranks = {u: 0 for u in nodes}
            self.subsets = {u: {u} for u in nodes}

        def find(self, u):
            return u if self.parents[u] == u else self.find(self.parents[u])

        def union(self, u, v):

            u_root, v_root = self.find(u), self.find(v)

            if self.ranks[u_root] < self.ranks[v_root]:
                self.parents[u_root] = v_root

                self.subsets[v_root] |= self.subsets[u_root]
                del self.subsets[u_root]

            elif self.ranks[u_root] > self.ranks[v_root]:
                self.parents[v_root] = u_root

                self.subsets[u_root] |= self.subsets[v_root]
                del self.subsets[v_root]

            else:
                self.parents[v_root] = u_root
                self.ranks[u_root] += 1

                self.subsets[u_root] |= self.subsets[v_root]
                del self.subsets[v_root]

    def min_cut(g):
        """Return a min cut of g.

        The procedure is based on Karger's algorithm [1].

        [1] D. Karger "Global Min-cuts in RNC and Other Ramifications of a Simple Mincut Algorithm".
        Proc. 4th Annual ACM-SIAM Symposium on Discrete Algorithms 1993.
        """
        edges = []
        weights = []
        sum_rate = 0

        for (u, v) in g.edges():
            edges.append((u, v))
            rate = g[u][v]["rate"]
            weights.append(rate)
            sum_rate += rate

        n_nodes = len(g.nodes())

        uf = UnionFind(g.nodes())

        sorted_edges = iter(
            np.random.choice(
                np.arange(len(edges)),
                size=len(edges),
                replace=False,
                p=np.array(weights) / sum_rate,
            )
        )

        while n_nodes > 2:
            u, v = edges[next(sorted_edges)]

            if uf.find(u) != uf.find(v):
                n_nodes -= 1
                uf.union(u, v)

        return uf.subsets.values()

    to_be_processed = [set(virtual.nodes())]
    partitions = []

    root = Node(
        frozenset(virtual.nodes()),
        cores=sum(virtual.req_cores(u) for u in virtual.nodes()),
        memory=sum(virtual.req_memory(u) for u in virtual.nodes()),
    )

    t = Tree(root)

    # to keep track of the Node associated to each of the partitions
    partitions_nodes = {frozenset(virtual.nodes()): root}

    while to_be_processed:
        p = to_be_processed.pop()
        if len(p) <= 1:
            partitions.append(p)
        else:
            if algo == "min_cut":
                p1, p2 = min_cut(virtual.g.subgraph(p))
            elif algo == "bisection":
                p1, p2 = kernighan_lin_bisection(virtual.g.subgraph(p), weight="rate")
            else:
                raise ValueError("undefined")

            # update tree
            parent = partitions_nodes[frozenset(p)]

            p1_node = Node(
                frozenset(p1),
                cores=sum(virtual.req_cores(u) for u in p1),
                memory=sum(virtual.req_memory(u) for u in p1),
                parent=parent,
            )

            p2_node = Node(
                frozenset(p2),
                cores=sum(virtual.req_cores(u) for u in p2),
                memory=sum(virtual.req_memory(u) for u in p2),
                parent=parent,
            )

            partitions_nodes[frozenset(p)].l = partitions_nodes[frozenset(p1)] = p1_node
            partitions_nodes[frozenset(p)].r = partitions_nodes[frozenset(p2)] = p2_node

            to_be_processed.append(p1)
            to_be_processed.append(p2)

    return t


class EmbedGreedy(EmbedSolver):
    @timeit
    def solve(self, **kwargs):

        algo = kwargs.get("algo", "bisection")

        partitions_tree = partition(self.virtual, algo=algo)

        # nodes are sorted in non increasing order according to the amount of resources (cpu, memory)
        # the formula used is : n_cores * 1000 + memory + outgoing_rate
        sorted_compute_nodes = sorted(
            self.physical.compute_nodes,
            key=lambda x: self.physical.cores(x) * 1000
            + self.physical.memory(x)
            + self.physical.rate_out(x),
            reverse=True,
        )

        for n_nodes_to_consider in range(
            self.lower_bound(), len(sorted_compute_nodes) + 1
        ):

            nodes_to_consider = sorted_compute_nodes[:n_nodes_to_consider]

            cores_used = defaultdict(int)
            memory_used = defaultdict(int)
            rate_used = defaultdict(int)
            assigned = defaultdict(list)

            res_node_mapping = {}
            res_link_mapping = {}

            # for each partition, starting from the biggest
            for node in partitions_tree.bfs_visit():
                # consider the physical nodes starting from the already selected ones
                for phy_node in nodes_to_consider:
                    try:
                        # check if the node resources are enough
                        if node.cores + cores_used[phy_node] > self.physical.cores(
                            phy_node
                        ) or node.memory + memory_used[phy_node] > self.physical.memory(
                            phy_node
                        ):
                            raise NodeResourceError

                        # check if outgoing communications can be performed and find a path
                        if sum(
                            self.virtual.req_rate(u, v)
                            for u in node.partition | set(assigned[phy_node])
                            for v in self.virtual.neighbors(u)
                            if v not in node.partition | set(assigned[phy_node])
                        ) > self.physical.rate_out(phy_node):
                            raise LinkCapacityError

                        temp_rate = defaultdict(int)
                        temp_paths = defaultdict(list)
                        # check if virtual links can be mapped
                        for (u, v) in [
                            (u, v)
                            for u in node.partition
                            for v in self.virtual.neighbors(u)
                            if v not in node.partition
                        ]:
                            if (
                                v in res_node_mapping
                                and res_node_mapping[v] != phy_node
                            ):

                                # find a path for the virtual link
                                path = self.physical.find_path(
                                    phy_node,
                                    res_node_mapping[v],
                                    req_rate=self.virtual.req_rate(u, v),
                                    used_rate=Counter(rate_used) + Counter(temp_rate),
                                )

                                # for each link in the path
                                for (i, j, device_id) in path:
                                    temp_rate[
                                        (i, j, device_id)
                                    ] += self.virtual.req_rate(u, v)
                                    temp_paths[(u, v)].append((i, device_id, j))

                        # update the partitions placed
                        partitions_tree.placed |= set(node.partition)

                        # update results
                        res_link_mapping.update(temp_paths)
                        for u in node.partition:
                            res_node_mapping[u] = phy_node
                            assigned[phy_node].append(u)

                        # update used resources
                        cores_used[phy_node] += node.cores
                        memory_used[phy_node] += node.memory
                        for k, v in temp_rate.items():
                            rate_used[k] += v
                        break

                    except (NodeResourceError, LinkCapacityError, NoPathFoundError):
                        pass

            # if all virtual nodes have been mapped return the solution
            if set(res_node_mapping) == set(self.virtual.nodes()):
                self.solution = Solution.build_solution(
                    self.virtual,
                    self.physical,
                    res_node_mapping,
                    res_link_mapping,
                    check_solution=False,
                )
                self.status = Solved
                return Solved

        else:
            self.status = Infeasible
            return Infeasible
