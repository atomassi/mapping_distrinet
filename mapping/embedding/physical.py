import json
import logging
import os
import warnings

import networkx as nx


class PhysicalNetwork(object):

    def __init__(self, g, grouped_interfaces=False):
        """Initialize the physical network with the graph g.

        grouped_interfaces is set to True if all the network interfaces between two physical nodes
        have been grouped into a single one.
        """
        self._g = g
        self.grouped_interfaces = grouped_interfaces
        self._log = logging.getLogger(__name__)

    @property
    def g(self):
        return self._g

    @property
    def compute_nodes(self):
        """Physical nodes able to run virtual nodes."""
        if not hasattr(self, '_compute'):
            self._compute = set(u for u in self.nodes() if self.cores(u) > 0 and self.memory(u) > 0)
        return self._compute

    @g.setter
    def g(self, g_new):
        warnings.warn("original physical network has been modified")
        self._g = g_new

    def edges(self, keys=False):
        """Return the edges of the graph."""
        return self._g.edges(keys=keys)

    def nodes(self):
        """Return the nodes of the graph."""
        return self._g.nodes()

    def cores(self, node):
        """Return the number of physical cores for a physical node."""
        if 'cores' in self._g.nodes[node]:
            return self._g.node[node]['cores']
        return 0

    def memory(self, node):
        """Return the amount of memory for a physical node."""
        if 'memory' in self._g.nodes[node]:
            return self._g.node[node]['memory']
        return 0

    def rate(self, i, j, device='dummy_interface'):
        """Return the maximum allowed rate for a physical link."""
        return self._g[i][j][device]['rate']

    def nw_interfaces(self, i, j):
        """Return the network interfaces for a link (i,j)."""
        return self._g[i][j]

    def neighbors(self, i):
        """Return the neighbors of a node."""
        return self._g[i]

    def associated_nw_interfaces(self, i, j):
        """Return the real interfaces associated with the link."""
        if not self.grouped_interfaces:
            raise ValueError("Defined only when interfaces are grouped")
        return self._g[i][j]['dummy_interface']['associated_interfaces']

    def rate_associated_nw_interface(self, i, j, device):
        """Return the rate of a real link interface."""
        if not self.grouped_interfaces:
            raise ValueError("Defined only when interfaces are grouped")
        return self._g[i][j]['dummy_interface']['associated_interfaces'][device]

    def number_of_nodes(self):
        return self._g.number_of_nodes()

    def find_path(self, source, target):
        """Given the physical network, return the path between the source and the target nodes."""

        if not hasattr(self, '_computed_paths'):
            self._computed_paths = {}

        # if the path has already been computed
        if (source, target) in self._computed_paths:
            return self._computed_paths[(source, target)]
        # check if the path from the destination to the source already exists
        elif (target, source) in self._computed_paths:
            res = self._computed_paths[(source, target)] = self._computed_paths[(target, source)][::-1]
            return res

        # otherwise compute a path and cache it
        path = [source]
        stack = [(u for u in self.neighbors(source))]
        while stack:
            children = stack[-1]
            child = next(children, None)
            if child is None:
                stack.pop()
                path.pop()
            else:
                if child == target:
                    path.append(target)
                    # return a path as a list of edges
                    res = self._computed_paths[(source, target)] = [
                        (path[i], path[i + 1]) if path[i] < path[i + 1] else (path[i + 1], path[i]) for i in
                        range(len(path) - 1)]
                    return res
                elif child not in path:
                    path.append(child)
                    stack.append((u for u in self.neighbors(child)))
        else:
            print("No path exists")
            exit(1)

    @classmethod
    def grid5000(cls, name, n_interfaces_to_consider=float('inf'), group_interfaces=False):
        """Import the physical network topology from a Grid5000 cluster json description."""

        g = nx.MultiGraph()
        # compute nodes
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "instances", "grid5k", name + ".json")) as f:
            data = json.load(f)

            for node in data['items']:
                # from byte to mebibyte
                g.add_node(node['uid'], cores=node['architecture']['nb_cores'] * node['architecture']['nb_procs'],
                           memory=node['main_memory']['ram_size'] / (1024 ** 2))

                n_added_interfaces = 0
                for interface, link in enumerate(node['network_adapters']):
                    if link['device'].startswith("eth") and link['enabled'] and link['driver'] == "ixgbe":
                        source, dest, device_name, device_rate = node['uid'], link['switch'], link['device'], link[
                            'rate'] / 10 ** 6
                        if not group_interfaces:
                            g.add_edge(source, dest, key=device_name, rate=device_rate)
                        else:
                            if not g.has_edge(source, dest):
                                g.add_edge(source, dest, key='dummy_interface', rate=device_rate,
                                           associated_interfaces={device_name: device_rate})
                            else:
                                g[source][dest]['dummy_interface']['rate'] += device_rate
                                g[source][dest]['dummy_interface']['associated_interfaces'][device_name] = device_rate

                        n_added_interfaces += 1
                        if n_added_interfaces == n_interfaces_to_consider:
                            break
        return cls(g, group_interfaces)

    @classmethod
    def crete_test_nw(cls):
        """Create a test physical network to run tests.

                         s3
                       /    \
                      s1     s2
                     /  \   /  \
                    h1  h2 h3  h4

        """
        # Nodes

        g = nx.MultiGraph()
        g.add_node("h1", cores=10, memory=64000)
        g.add_node("h2", cores=10, memory=64000)
        g.add_node("h3", cores=10, memory=64000)
        g.add_node("h4", cores=10, memory=64000)

        g.add_node("s1", cores=0, memory=0)
        g.add_node("s2", cores=0, memory=0)
        g.add_node("s3", cores=0, memory=0)

        # Links
        g.add_edge("h1", "s1", key="eth0", rate=10000)
        g.add_edge("h2", "s1", key="eth0", rate=10000)

        g.add_edge("h3", "s2", key="eth0", rate=10000)
        g.add_edge("h4", "s2", key="eth0", rate=10000)

        g.add_edge("s1", "s3", key="eth0", rate=10000)
        g.add_edge("s2", "s3", key="eth0", rate=10000)

        return cls(nx.freeze(g))

    @classmethod
    def from_mininet(cls, mininet_topo, n_interfaces_to_consider=float('inf'), group_interfaces=False):
        """Create a PhysicalNetwork from a mininet Topo network."""

        from mininet.topo import Topo

        assert isinstance(mininet_topo, Topo), "Invalid Network Format"

        g = nx.MultiGraph()

        for u in mininet_topo.nodes():
            g.add_node(u, cores=mininet_topo.nodeInfo(u).get('cores', 0),
                       memory=mininet_topo.nodeInfo(u).get('memory', 0))

        for (u, v, interfaces_list) in mininet_topo.iterLinks(withInfo=True):
            n_added_interfaces = 0
            for device_name in interfaces_list['nw_interfaces']:
                if not group_interfaces:
                    g.add_edge(u, v, key=device_name, rate=interfaces_list['nw_interfaces'][device_name])
                else:
                    if not g.has_edge(u, v):
                        g.add_edge(u, v, key='dummy_interface', rate=interfaces_list['nw_interfaces'][device_name],
                                   associated_interfaces={device_name: interfaces_list['nw_interfaces'][device_name]})
                    else:
                        g[u][v]['dummy_interface']['rate'] += interfaces_list['nw_interfaces'][device_name]
                        g[u][v]['dummy_interface']['associated_interfaces'][device_name] = \
                            interfaces_list['nw_interfaces'][device_name]

                n_added_interfaces += 1
                if n_added_interfaces == n_interfaces_to_consider:
                    break

        return cls(nx.freeze(g))

    @classmethod
    def from_file(cls, filename="example", n_interfaces_to_consider=float('inf'), group_interfaces=False):
        """Create a PhysicalNetwork from a json file."""

        g = nx.MultiGraph()

        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "instances", "generic",
                               filename + ".json")) as f:

            data = json.load(f)

            for node_info in data['nodes']:
                g.add_node(node_info['id'], cores=node_info.get('cores', 0), memory=node_info.get('memory', 0))

            for link_info in data['links']:
                u, v, nw_interfaces = link_info['source'], link_info['target'], link_info['nw_interfaces']

                n_added_interfaces = 0
                for device in nw_interfaces:
                    device_name, rate = device['device_name'], device['rate']

                    if not group_interfaces:
                        g.add_edge(u, v, key=device_name, rate=rate)
                    else:
                        if not g.has_edge(u, v):
                            g.add_edge(u, v, key='dummy_interface', rate=rate,
                                       associated_interfaces={device_name: rate})
                        else:
                            g[u][v]['dummy_interface']['rate'] += rate
                            g[u][v]['dummy_interface']['associated_interfaces'][device_name] = rate

                    n_added_interfaces += 1
                    if n_added_interfaces == n_interfaces_to_consider:
                        break

        return cls(nx.freeze(g))


if __name__ == "__main__":

    from mininet.topo import Topo

    mn_topo = Topo()

    master1 = mn_topo.addHost('Master1', cores=2)
    node1 = mn_topo.addHost('Node1', cores=2)
    sw = mn_topo.addSwitch('SW')
    mn_topo.addLink(master1, sw, nw_interfaces={"eth0": 1000})
    mn_topo.addLink(node1, sw, nw_interfaces={"eth0": 1000})

    p1 = PhysicalNetwork.from_mininet(mn_topo, group_interfaces=False)
    p2 = PhysicalNetwork.from_mininet(mn_topo, group_interfaces=True)
    p3 = PhysicalNetwork.from_file(group_interfaces=False)
    p4 = PhysicalNetwork.from_file(group_interfaces=True)

    for p in p1, p2, p3, p4:
        print(str(p))
        print(p.nodes())
        print(p.edges(keys=True))
        print(p.find_path('Master1', 'Node1'))
