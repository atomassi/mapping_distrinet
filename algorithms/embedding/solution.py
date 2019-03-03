import logging
from collections import defaultdict

from algorithms.constants import EmptySolutionError, AssignmentError, NodeResourceError, LinkCapacityError


class LinkMap(object):
    """Virtual Link algorithms to physical resources.

    Given a virtual link (u,v) a LinkMap represents a algorithms:
    - from both the physical node and the interface where u is hosted
    - to both the physical node and the interface where v is hosted

    Also, it specifies the amount of rate (in the range [0,1]) to route in this path.
    """

    def __init__(self, s_node, s_device, d_node, d_device, f_rate=1):
        self.s_node = s_node
        self.s_device = s_device
        self.d_node = d_node
        self.d_device = d_device
        self.f_rate = f_rate

    def __str__(self):
        return f"source: {self.s_node}, source_device: {self.s_device}, destination node: {self.d_node}," \
            f" destination device: {self.d_device}, rate to route: {self.f_rate}"


class Solution(object):
    """Represent the output of the placement algorithms.

    Examples
    --------
    >>> solution.node_info(u)
    grisou-6
    >>> solution.node_info(v)
    grisou-7
    >>> solution.link_info((u,v))
    [<algorithms.embedding.solution.LinkMap object at 0x113794a90>]
    >>> for link_map in solution.link_info((u,v)):
    ...        print(link_map.__dict__)
    {'s_node': 'grisou-6', 's_device': 'eth1', 'd_node': 'grisou-7', 'd_device': 'eth3', 'f_rate': 1}

    """

    def __init__(self, node_mapping, link_mapping):
        self.node_mapping = node_mapping
        self.link_mapping = link_mapping
        self.n_machines_used = len(set(node_mapping.values()))
        self._log = logging.getLogger(__name__)

    def node_info(self, node):
        """Return the algorithms for the virtual node."""
        return self.node_mapping[node]

    def link_info(self, link):
        """Return the algorithms for the virtual link."""
        try:
            return self.link_mapping[link]
        except KeyError:
            return []

    def output(self):
        raise NotImplementedError

    @staticmethod
    def verify_solution(virtual, physical, node_mapping, link_path):
        """check if the solution is correct"""

        #
        # empty solution or invalid solution
        #
        if not node_mapping: raise EmptySolutionError

        #
        # each virtual node is assigned to a physical node
        #
        for virtual_node in virtual.nodes():
            if not virtual_node in node_mapping:
                raise AssignmentError(virtual_node)
        #
        # each virtual link is assigned
        #
        for (u, v) in virtual.sorted_edges():
            if not (u, v) in link_path and node_mapping[u] != node_mapping[v]:
                raise AssignmentError((u, v))
            elif node_mapping[u] != node_mapping[v]:
                if len(link_path[(u, v)]) < 2:
                    raise AssignmentError((u, v))

        #
        # resource usage on nodes
        #
        node_cores_used = defaultdict(int)
        node_memory_used = defaultdict(int)
        for virtual_node, physical_node in node_mapping.items():
            # cpu limit is not exceeded
            node_cores_used[physical_node] += virtual.req_cores(virtual_node)
            if node_cores_used[physical_node] > physical.cores(physical_node):
                raise NodeResourceError(physical_node, "cpu cores", node_cores_used[physical_node],
                                        physical.cores(physical_node))
            # memory limit is not exceeded
            node_memory_used[physical_node] += virtual.req_memory(virtual_node)
            if node_memory_used[physical_node] > physical.memory(physical_node):
                raise NodeResourceError(physical_node, "memory", node_memory_used[physical_node],
                                        physical.memory(physical_node))

        #
        # resource usage on links
        #
        used_link_resources = {(i, j): {interface: 0 for interface in physical.nw_interfaces(i, j)}
                               for (i, j) in physical.edges()}

        for (u, v) in link_path:
            for s1, i1, t1 in link_path[(u, v)]:
                try:
                    used_link_resources[(s1, t1)][i1] += virtual.req_rate(u, v)
                except KeyError:
                    used_link_resources[(t1, s1)][i1] += virtual.req_rate(u, v)

        for (i, j) in physical.edges():

            for interface in physical.nw_interfaces(i, j):
                if used_link_resources[(i, j)][interface] > physical.rate(i, j, interface):
                    raise LinkCapacityError(f"Capacity exceeded on ({i},{j})")

        # delay requirements are respected
        # @todo to be defined

    @classmethod
    def build_solution(cls, virtual, physical, node_mapping, link_path, check_solution=True):
        if check_solution:
            Solution.verify_solution(virtual, physical, node_mapping, link_path)

        if physical.grouped_interfaces:
            link_mapping = {}
            rate_interfaces = {
                (i, j): {interface: physical.rate_associated_nw_interface(i, j, interface) for interface in
                         physical.associated_nw_interfaces(i, j)} for (i, j) in physical.edges()}

            for (u, v) in virtual.sorted_edges():
                phy_u, phy_v = node_mapping[u], node_mapping[v]
                # if virtual nodes are mapped on two different physical nodes
                if phy_u != phy_v:
                    link_mapping[(u, v)] = []
                    link_mapping[(v, u)] = []
                    path = link_path[(u, v)]
                    u_source, _, u_dest = path[0]
                    v_source, _, v_dest = path[-1]

                    interfaces_u = rate_interfaces[(u_source, u_dest)] \
                        if (u_source, u_dest) in rate_interfaces else rate_interfaces[(u_dest, u_source)]
                    interfaces_v = rate_interfaces[(v_source, v_dest)] \
                        if (v_source, v_dest) in rate_interfaces else rate_interfaces[(v_dest, v_source)]

                    # until we don't map all the requested rate
                    requested_rate = virtual.req_rate(u, v)
                    to_be_mapped = requested_rate

                    while to_be_mapped > 0:
                        # take the interfaces with the highest available rate on the physical nodes
                        # where the endpoint of u and v are mapped
                        interface_u_highest_rate = max(interfaces_u, key=interfaces_u.get)
                        interface_v_highest_rate = max(interfaces_v, key=interfaces_v.get)

                        # the amount of rate that can be mapped is the mininum between rate to be mapped and the available one
                        mapped_rate = min(to_be_mapped, interfaces_u[interface_u_highest_rate],
                                          interfaces_v[interface_v_highest_rate])

                        # update the algorithms

                        link_mapping[(u, v)].append(
                            LinkMap(u_source, interface_u_highest_rate, v_dest, interface_v_highest_rate,
                                    mapped_rate / float(requested_rate)))
                        link_mapping[(v, u)].append(
                            LinkMap(v_dest, interface_v_highest_rate, u_source, interface_u_highest_rate,
                                    mapped_rate / float(requested_rate)))

                        # update available rate
                        to_be_mapped -= mapped_rate
                        interfaces_u[interface_u_highest_rate] -= mapped_rate
                        interfaces_v[interface_v_highest_rate] -= mapped_rate

        else:
            link_mapping = {}
            for (u, v), path in link_path.items():
                s_node, s_device, _ = path[0]
                _, d_device, d_node = path[-1]
                link_mapping[(u, v)] = [LinkMap(s_node, s_device, d_node, d_device)]
                link_mapping[(v, u)] = [LinkMap(d_node, d_device, s_node, s_device)]

        return cls(node_mapping, link_mapping)

    def __str__(self):
        return "\n".join(
            [f"virtual node {virtual_node} mapped on physical node {physical_node}" for virtual_node, physical_node in
             self.node_mapping.items()]) + "\n" + "\n".join(
            [f"virtual link {virtual_link} mapped on physical path {str(physical_path)}" for virtual_link, physical_path
             in self.link_mapping.items()])
