import json
import logging
import os

import networkx as nx

from distriopt.constants import NoPathFoundError
from distriopt.decorators import cached, cachedproperty, implemented_if_true

_log = logging.getLogger(__name__)


class PhysicalNetwork(object):
    "Utility class to model the physical network. Uses networkx.MultiGraph."

    def __init__(self, g, grouped_interfaces=False):
        self._g = g
        self.grouped_interfaces = grouped_interfaces

    @property
    def g(self):
        return self._g

    @cachedproperty
    def compute_nodes(self):
        """Physical nodes able to run virtual nodes."""
        return set(u for u in self.nodes() if self.cores(u) > 0 and self.memory(u) > 0)

    def edges(self, keys=False):
        """Return the edges of the graph."""
        return self._g.edges(keys=keys)

    def nodes(self):
        """Return the nodes of the graph."""
        return self._g.nodes()

    def cores(self, node):
        """Return the number of physical cores for a physical node."""
        return self._g.node[node].get("cores", 0)

    def memory(self, node):
        """Return the amount of memory for a physical node."""
        return self._g.node[node].get("memory", 0)

    def rate(self, i, j, device_id="dummy"):
        """Return the rate associated to a physical link and interface id."""
        return self._g[i][j][device_id]["rate"]

    @cached
    def rate_out(self, i):
        """Return the total rate supported by the node interface(s)."""
        return sum(
            self.rate(i, j, device_id)
            for j in self.neighbors(i)
            for device_id in self.interfaces_ids(i, j)
        )

    def interfaces_ids(self, i, j):
        """Return the network interfaces identifiers for a link (i,j)."""
        return self._g[i][j]

    def interface_name(self, i, j, device_id):
        """Return the network interfaces *from i to j* (order matters) corresponding to a device id."""
        return self._g[i][j][device_id]["devices"][i]

    def neighbors(self, i):
        """Return the neighbor nodes for a node i."""
        return self._g[i]

    @implemented_if_true("grouped_interfaces")
    def associated_nw_interfaces(self, i, j):
        """Return the real interfaces associated with the link."""
        return self._g[i][j]["dummy"]["associated_devices"]

    @implemented_if_true("grouped_interfaces")
    def rate_associated_nw_interface(self, i, j, device_id):
        """Return the rate associated to a real link interface."""
        return self._g[i][j]["dummy"]["associated_devices"][device_id]["rate"]

    def name_associated_nw_interface(self, i, j, device_id):
        """Return the name associated to a real link interface."""
        if not self.grouped_interfaces:
            raise ValueError("Defined only when interfaces are grouped")
        return self._g[i][j]["dummy"]["associated_devices"][device_id][i]

    def number_of_nodes(self):
        return self._g.number_of_nodes()

    def find_path(self, source, target, req_rate=0, used_rate={}):
        """Given the physical network, return the path between the source and the target nodes."""

        path = [source]
        interfaces_used = [None]

        stack = [(u for u in self.neighbors(source))]

        while stack:
            prev = path[-1]
            curr = next(stack[-1], None)
            # if generator has not been exhausted
            # take the first device which can support the requested rate
            if curr is None:
                stack.pop()
                path.pop()
                interfaces_used.pop()
            else:
                device_id = next(
                    (
                        device_id
                        for device_id in self.interfaces_ids(prev, curr)
                        if self.rate(prev, curr, device_id)
                        >= req_rate
                        + used_rate.get((prev, curr, device_id), 0)
                        + used_rate.get((curr, prev, device_id), 0)
                    ),
                    None,
                )

                if device_id is not None:
                    if curr == target:
                        interfaces_used.append(device_id)
                        path.append(target)
                        # return a path as a list (i, j, device_id)
                        res = [
                            (path[i], path[i + 1], device_id)
                            for (i, device_id) in zip(
                                range(len(path) - 1), interfaces_used[1:]
                            )
                        ]
                        return res
                    elif curr not in path:
                        interfaces_used.append(device_id)
                        path.append(curr)
                        stack.append((u for u in self.neighbors(curr)))
        else:
            raise NoPathFoundError

    @classmethod
    def from_mininet(
        cls, mininet_topo, n_interfaces_to_consider=float("inf"), group_interfaces=False
    ):
        """Create a PhysicalNetwork from a mininet Topo network."""

        from mininet.topo import Topo

        assert isinstance(mininet_topo, Topo), "Invalid Network Format"

        g = nx.MultiGraph()

        for u in mininet_topo.nodes():
            g.add_node(
                u,
                cores=mininet_topo.nodeInfo(u).get("cores", 0),
                memory=mininet_topo.nodeInfo(u).get("memory", 0),
            )

        for (u, v, attrs) in mininet_topo.iterLinks(withInfo=True):
            n_added_interfaces = 0

            u_port, v_port, rate = attrs["port1"], attrs["port2"], attrs["rate"]

            if not group_interfaces:
                g.add_edge(u, v, rate=rate, devices={u: u_port, v: v_port})
            else:
                if not g.has_edge(u, v):
                    g.add_edge(
                        u,
                        v,
                        key="dummy",
                        rate=rate,
                        associated_devices={
                            n_added_interfaces: {u: u_port, v: v_port, "rate": rate}
                        },
                    )
                else:
                    g[u][v]["dummy"]["rate"] += rate
                    g[u][v]["dummy"]["associated_devices"][n_added_interfaces] = {
                        u: u_port,
                        v: v_port,
                        "rate": rate,
                    }

            n_added_interfaces += 1
            if n_added_interfaces == n_interfaces_to_consider:
                break

        return cls(nx.freeze(g), group_interfaces)

    @classmethod
    def from_files(
        cls, *files, n_interfaces_to_consider=float("inf"), group_interfaces=False
    ):
        """Create a PhysicalNetwork from json files."""

        g = nx.MultiGraph()

        for file in files:
            # filename can be the path to a file or the name of a local topology
            filepath = (
                file
                if os.path.isabs(file)
                else os.path.join(
                    os.path.dirname(__file__), "instances", file + ".json"
                )
            )

            with open(filepath) as f:

                data = json.load(f)

                for node_info in data["nodes"]:
                    g.add_node(
                        node_info["id"],
                        cores=node_info.get("cores", 0),
                        memory=node_info.get("memory", 0),
                    )

                for link_info in data["links"]:
                    u, v, devices = (
                        link_info["source"],
                        link_info["target"],
                        link_info["devices"],
                    )

                    n_added_interfaces = 0
                    for device in devices:
                        source_device, target_device, rate = (
                            device["source_device"],
                            device["target_device"],
                            device["rate"],
                        )

                        if not group_interfaces:
                            g.add_edge(
                                u,
                                v,
                                rate=rate,
                                devices={u: source_device, v: target_device},
                            )
                        else:
                            if not g.has_edge(u, v):
                                g.add_edge(
                                    u,
                                    v,
                                    key="dummy",
                                    rate=rate,
                                    associated_devices={
                                        n_added_interfaces: {
                                            u: source_device,
                                            v: target_device,
                                            "rate": rate,
                                        }
                                    },
                                )
                            else:
                                g[u][v]["dummy"]["rate"] += rate
                                g[u][v]["dummy"]["associated_devices"][
                                    n_added_interfaces
                                ] = {u: source_device, v: target_device, "rate": rate}

                        n_added_interfaces += 1
                        if n_added_interfaces == n_interfaces_to_consider:
                            break

        # @TODO add support for disconnected physical networks
        if not nx.is_connected(g):
            raise ValueError("Physical Network is not connected")

        return cls(nx.freeze(g), group_interfaces)

    @classmethod
    def create_test_nw(cls, cores=4, memory=4000, rate=10000, group_interfaces=False):
        """Create a test physical network to run tests.

                         s1
                       /    \
                      h1     h2

        """

        # Nodes
        g = nx.MultiGraph()
        g.add_node("h1", cores=cores, memory=memory)
        g.add_node("h2", cores=cores, memory=memory)
        g.add_node("s1", cores=0, memory=0)

        # Links

        if not group_interfaces:
            g.add_edge("h1", "s1", devices={"h1": "eth0", "s1": "eth0"}, rate=rate)
            g.add_edge("h1", "s1", devices={"h1": "eth1", "s1": "eth1"}, rate=rate)
            g.add_edge("h2", "s1", devices={"h2": "eth0", "s1": "eth2"}, rate=rate)
            g.add_edge("h2", "s1", devices={"h2": "eth1", "s1": "eth3"}, rate=rate)

        else:
            g.add_edge(
                "h1",
                "s1",
                key="dummy",
                associated_devices={
                    0: {"h1": "eth0", "s1": "eth0", "rate": rate},
                    1: {"h1": "eth1", "s1": "eth1", "rate": rate},
                },
                rate=rate * 2,
            )
            g.add_edge(
                "h2",
                "s1",
                key="dummy",
                associated_devices={
                    0: {"h2": "eth0", "s1": "eth2", "rate": rate},
                    1: {"h2": "eth1", "s1": "eth2", "rate": rate},
                },
                rate=rate * 2,
            )

        return cls(nx.freeze(g), grouped_interfaces=group_interfaces)
