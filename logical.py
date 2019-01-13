import logging
import warnings

import networkx as nx


class LogicalNetwork(object):

    def __init__(self, g):
        self._g = g
        self._log = logging.getLogger(__name__)

    @property
    def g(self):
        return self._g

    @g.setter
    def g(self, g_new):
        warnings.warn("original logical network has been modified")
        self._g = g_new

    def edges(self):
        return self._g.edges()

    def sorted_edges(self):
        return set((u, v) if u < v else (v, u) for (u, v) in self.edges())

    def nodes(self):
        return self._g.nodes()

    def requested_cores(self, node):
        return self._g.nodes[node]['cores']

    def requested_memory(self, node):
        return self._g.nodes[node]['memory']

    def requested_link_rate(self, i, j):
        return self._g[i][j]['rate']

    def get_nw_interfaces(self, i, j):
        return self._g[i][j]

    def get_neighbors(self, i):
        return self._g[i]

    @classmethod
    def create_fat_tree(cls, k=2, density=2, node_req_cores=2, node_req_memory=1000000, link_req_rate=50000000):
        """create a K-ary FatTree
        """
        assert k > 1, "k should be greater than 1"
        nb_pods = k
        nb_core_switches = int((k / 2) ** 2)
        nb_aggr_switches = int(k * k / 2)
        nb_edge_switches = int(k * k / 2)
        nb_hosts = nb_edge_switches * density

        hosts = [f'host_{i}' for i in range(1, nb_hosts + 1)]
        core_switches = [f'core_{i}' for i in range(1, nb_core_switches + 1)]
        aggr_switches = [f'aggr_{i}' for i in range(1, nb_aggr_switches + 1)]
        edge_switches = [f'edge_{i}' for i in range(1, nb_edge_switches + 1)]

        g = nx.Graph()
        g.add_nodes_from(hosts)
        g.add_nodes_from(core_switches)
        g.add_nodes_from(aggr_switches)
        g.add_nodes_from(edge_switches)

        # Core to Aggr
        end = int(nb_pods / 2)
        for x in range(0, nb_aggr_switches, end):
            for i in range(0, end):
                for j in range(0, end):
                    g.add_edge(core_switches[i * end + j], aggr_switches[x + i])

        # Aggr to Edge
        for x in range(0, nb_aggr_switches, end):
            for i in range(0, end):
                for j in range(0, end):
                    g.add_edge(aggr_switches[x + i], edge_switches[x + j])

        # Edge to Host
        for x in range(0, nb_edge_switches):
            for i in range(density):
                g.add_edge(edge_switches[x], hosts[density * x + i])

        for node in g.nodes():
            g.node[node]['cores'] = node_req_cores
            g.node[node]['memory'] = node_req_memory
        for edge in g.edges():
            g.edges[edge]['rate'] = link_req_rate

        return cls(g)

    @classmethod
    def read_from_file(cls, filename):
        raise NotImplementedError
