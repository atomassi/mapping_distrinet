import json
import logging
import os

import networkx as nx


class PhysicalNetwork(object):
    "Utility class to model the physical network. Uses networkx.MultiGraph."

    def __init__(self, g, grouped_interfaces=False):
        self._g = g
        self.grouped_interfaces = grouped_interfaces
        self._log = logging.getLogger(__name__)

    @property
    def compute_nodes(self):
        """Physical nodes able to run virtual nodes."""
        if not hasattr(self, '_compute'):
            self._compute_nodes = set(u for u in self.nodes() if self.cores(u) > 0 and self.memory(u) > 0)
        return self._compute_nodes

    def edges(self, keys=False):
        """Return the edges of the graph."""
        return self._g.edges(keys=keys)

    def nodes(self):
        """Return the nodes of the graph."""
        return self._g.nodes()

    def cores(self, node):
        """Return the number of physical cores for a physical node."""
        return self._g.node[node].get('cores', 0)

    def memory(self, node):
        """Return the amount of memory for a physical node."""
        return self._g.node[node].get('memory', 0)

    def rate(self, i, j, device_id='dummy'):
        """Return the maximum allowed rate for a physical link."""
        return self._g[i][j][device_id]['rate']

    def interfaces_ids(self, i, j):
        """Return the network interfaces identifiers for a link (i,j)."""
        return self._g[i][j]

    def interface_name(self, i, j, device_id):
        """Return the network interfaces *from i to j* (order matters) corresponding to a device id."""
        return self._g[i][j][device_id]['devices'][i]

    def neighbors(self, i):
        """Return the neighbor nodes for a node i."""
        return self._g[i]

    def associated_nw_interfaces(self, i, j):
        """Return the real interfaces associated with the link."""
        if not self.grouped_interfaces:
            raise ValueError("Defined only when interfaces are grouped")
        return self._g[i][j]['dummy']['associated_devices']

    def rate_associated_nw_interface(self, i, j, device_id):
        """Return the rate associated to a real link interface."""
        if not self.grouped_interfaces:
            raise ValueError("Defined only when interfaces are grouped")
        return self._g[i][j]['dummy']['associated_devices'][device_id]['rate']

    def name_associated_nw_interface(self, i, j, device_id):
        """Return the name associated to a real link interface."""
        if not self.grouped_interfaces:
            raise ValueError("Defined only when interfaces are grouped")
        return self._g[i][j]['dummy']['associated_devices'][device_id][i]

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
            raise ValueError("No path exists")

    @classmethod
    def from_mininet(cls, mininet_topo, n_interfaces_to_consider=float('inf'), group_interfaces=False):
        """Create a PhysicalNetwork from a mininet Topo network."""

        from mininet.topo import Topo

        assert isinstance(mininet_topo, Topo), "Invalid Network Format"

        g = nx.MultiGraph()

        for u in mininet_topo.nodes():
            g.add_node(u, cores=mininet_topo.nodeInfo(u).get('cores', 0),
                       memory=mininet_topo.nodeInfo(u).get('memory', 0))

        for (u, v, attrs) in mininet_topo.iterLinks(withInfo=True):
            n_added_interfaces = 0

            u_port, v_port, rate = attrs['port1'], attrs['port2'], attrs['rate']

            if not group_interfaces:
                g.add_edge(u, v, rate=rate, devices={u: u_port, v: v_port})
            else:
                if not g.has_edge(u, v):
                    g.add_edge(u, v, key='dummy', rate=rate,
                               associated_devices={n_added_interfaces: {u: u_port, v: v_port, 'rate': rate}})
                else:
                    g[u][v]['dummy']['rate'] += rate
                    g[u][v]['dummy']['associated_devices'][n_added_interfaces] = {u: u_port, v: v_port, 'rate': rate}

            n_added_interfaces += 1
            if n_added_interfaces == n_interfaces_to_consider:
                break

        return cls(nx.freeze(g), group_interfaces)

    @classmethod
    def from_files(cls, *filenames, n_interfaces_to_consider=float('inf'), group_interfaces=False):
        """Create a PhysicalNetwork from a json file."""

        g = nx.MultiGraph()

        for filename in filenames:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "instances", filename + ".json")) as f:

                data = json.load(f)

                for node_info in data['nodes']:
                    g.add_node(node_info['id'], cores=node_info.get('cores', 0), memory=node_info.get('memory', 0))

                for link_info in data['links']:
                    u, v, devices = link_info['source'], link_info['target'], link_info['devices']

                    n_added_interfaces = 0
                    for device in devices:
                        source_device, target_device, rate = device['source_device'], device['target_device'], device[
                            'rate']

                        if not group_interfaces:
                            g.add_edge(u, v, rate=rate, devices={u: source_device, v: target_device})
                        else:
                            if not g.has_edge(u, v):
                                g.add_edge(u, v, key='dummy', rate=rate,
                                           associated_devices={
                                               n_added_interfaces: {u: source_device, v: target_device, 'rate': rate}})
                            else:
                                g[u][v]['dummy']['rate'] += rate
                                g[u][v]['dummy']['associated_devices'][n_added_interfaces] = {u: source_device,
                                                                                              v: target_device,
                                                                                              'rate': rate}

                        n_added_interfaces += 1
                        if n_added_interfaces == n_interfaces_to_consider:
                            break

        # @TODO add support for disconnected physical networks
        if not nx.is_connected(g):
            raise ValueError("Physical Network is not connected")

        return cls(nx.freeze(g), group_interfaces)

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
        g.add_edge("h1", "s1", devices={"h1": "eth0", "s1": "eth1"}, rate=10000)
        g.add_edge("h1", "s1", devices={"h1": "eth66", "s1": "eth67"}, rate=10000)

        g.add_edge("h2", "s1", devices={"h2": "eth2", "s1": "eth3"}, rate=10000)

        g.add_edge("h3", "s2", devices={"h3": "eth4", "s2": "eth5"}, rate=10000)
        g.add_edge("h4", "s2", devices={"h4": "eth6", "s2": "eth7"}, rate=10000)

        g.add_edge("s1", "s3", devices={"s1": "eth8", "s3": "eth9"}, rate=10000)
        g.add_edge("s2", "s3", devices={"s2": "eth10", "s3": "eth11"}, rate=10000)

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
