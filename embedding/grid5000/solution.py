import logging
from collections import defaultdict

from embedding.exceptions import EmptySolutionError, AssignmentError, NodeResourceError, LinkCapacityError


class Solution(object):
    def __init__(self, logical, physical, res_node_mapping, res_link_mapping):
        self.logical = logical
        self.physical = physical
        self.res_node_mapping = res_node_mapping
        self.res_link_mapping = res_link_mapping
        self._log = logging.getLogger(__name__)

    def output(self):
        raise NotImplementedError

    def verify_solution(self):
        """check if the solution is correct
        """
        #
        # empty solution or invalid solution
        #
        if not self.res_node_mapping:
            raise EmptySolutionError
        #
        # each logical node is assigned to a physical node
        #
        for logical_node in self.logical.nodes():
            if not logical_node in self.res_node_mapping:
                raise AssignmentError(logical_node)
            else:
                self._log.info(f"Logical Node {logical_node} assigned to {self.res_node_mapping[logical_node]}")
        #
        # each logical link is assigned
        #
        for logical_link in self.logical.edges():
            (u, v) = logical_link
            if not logical_link in self.res_link_mapping and self.res_node_mapping[u] != self.res_node_mapping[v]:
                raise AssignmentError(logical_link)
            elif self.res_node_mapping[u] != self.res_node_mapping[v]:
                sum_rate = 0
                for (source_node, source_interface, _, dest_node, dest_interface, _, rate_on_it) in \
                        self.res_link_mapping[
                            (u, v)]:
                    sum_rate += rate_on_it
                    if source_node != self.res_node_mapping[u] or dest_node != self.res_node_mapping[v]:
                        raise AssignmentError(logical_link)
                if sum_rate != 1:
                    raise AssignmentError(logical_link)

        #
        # resource usage on nodes
        #
        # dict -> physical node: CPU cores used on it
        cpu_used_node = defaultdict(int)
        # dict -> physical node: memory used on it
        memory_used_node = defaultdict(int)
        # compute resources used
        for logical_node, physical_node in self.res_node_mapping.items():
            cpu_used_node[physical_node] += self.logical.req_cores(logical_node)
            memory_used_node[physical_node] += self.logical.req_memory(logical_node)
        # cpu limit is not exceeded
        for physical_node, cpu_cores_used in cpu_used_node.items():
            node_cores = self.physical.cores(physical_node)
            self._log.info(f"Physical Node {physical_node}: cpu cores used {cpu_cores_used} capacity {node_cores}")
            if cpu_cores_used > self.physical.cores(physical_node):
                raise NodeResourceError(physical_node, "cpu cores", cpu_cores_used, node_cores)
        # memory limit is not exceeded
        for physical_node, memory_used in memory_used_node.items():
            node_memory = self.physical.memory(physical_node)
            self._log.info(f"Physical Node {physical_node}: memory used {memory_used} capacity {node_memory}")
            if memory_used > self.physical.memory(physical_node):
                raise NodeResourceError(physical_node, "memory", memory_used, node_memory)
        #
        # resource usage on links
        #
        # dict -> physical link: rate used on it
        #
        if not self.physical.grouped_interfaces:
            used_link_resources = {(i, j): {interface: 0 for interface in self.physical.nw_interfaces(i, j)} for
                                   (i, j)
                                   in self.physical.edges()}
        else:
            used_link_resources = {(i, j): {interface: 0 for interface in self.physical.associated_nw_interfaces(i, j)}
                                   for
                                   (i, j) in self.physical.edges()}
        for (u, v) in self.res_link_mapping:
            for (s1, i1, t1, s2, i2, t2, rate_on_it) in self.res_link_mapping[(u, v)]:
                try:
                    used_link_resources[(s1, t1)][i1] += rate_on_it * self.logical.req_rate(u, v)
                except KeyError:
                    used_link_resources[(t1, s1)][i1] += rate_on_it * self.logical.req_rate(u, v)

                try:
                    used_link_resources[(s2, t2)][i2] += rate_on_it * self.logical.req_rate(u, v)
                except KeyError:
                    used_link_resources[(t2, s2)][i2] += rate_on_it * self.logical.req_rate(u, v)

        for (i, j) in self.physical.edges():
            nw_interfaces = self.physical.nw_interfaces(i, j) \
                if not self.physical.grouped_interfaces else self.physical.associated_nw_interfaces(i, j)
            for interface in nw_interfaces:
                link_rate = self.physical.rate(i, j, interface) \
                    if not self.physical.grouped_interfaces else self.physical.rate_associated_nw_interface(i, j,
                                                                                                            interface)

                if used_link_resources[(i, j)][interface] > link_rate:
                    print(used_link_resources)
                    raise LinkCapacityError((i, j, interface), used_link_resources[(i, j)][interface], link_rate)

        # delay requirements are respected
        # @todo to be defined

    @classmethod
    def map_to_multiple_interfaces(cls, logical, physical, res_node_mapping, res_link_mapping):
        """Given a solution for the physical network in which interfaces towards the same node have been
           grouped into a single one, it finds a solution for the original physical network.
        """
        res_link_mapping_multiple_interfaces = {}
        rate_on_nodes_interfaces = {
            (i, j): {interface: physical.rate_associated_nw_interface(i, j, interface) for interface in
                     physical.associated_nw_interfaces(i, j)} for (i, j) in physical.edges()}
        for (u, v) in logical.edges():
            physical_u, physical_v = res_node_mapping[u], res_node_mapping[v]
            # if logical nodes are mapped on two different physical nodes
            if physical_u != physical_v:
                res_link_mapping_multiple_interfaces[(u, v)] = []
                # for each mapping in the physical network with grouped interfaces
                # (even in this case a
                u_source, _, u_dest, v_source, _, v_dest, rate_mapped = res_link_mapping[(u, v)][0]
                interfaces_u = rate_on_nodes_interfaces[(u_source, u_dest)] if (u_source,
                                                                                u_dest) in rate_on_nodes_interfaces else \
                    rate_on_nodes_interfaces[(u_dest, u_source)]
                interfaces_v = rate_on_nodes_interfaces[(v_source, v_dest)] if (v_source,
                                                                                v_dest) in rate_on_nodes_interfaces else \
                    rate_on_nodes_interfaces[(v_dest, v_source)]
                # until we don't map all the requested rate
                requested_rate = logical.req_rate(u, v)
                to_be_mapped = requested_rate
                while to_be_mapped > 0:
                    # take the interfaces with the highest available rate on the physical nodes
                    # where the endpoint of u and v are mapped
                    interface_u_highest_rate = max(interfaces_u, key=interfaces_u.get)
                    interface_v_highest_rate = max(interfaces_v, key=interfaces_v.get)
                    # the amount of rate that can be mapped is the mininum between rate to be mapped and the available one
                    mapped_rate = min(requested_rate, interfaces_u[interface_u_highest_rate],
                                      interfaces_v[interface_v_highest_rate])
                    # update the mapping
                    res_link_mapping_multiple_interfaces[(u, v)].append((u_source, interface_u_highest_rate, u_dest,
                                                                         v_source, interface_v_highest_rate, v_dest,
                                                                         mapped_rate / float(requested_rate)))
                    # update available rate
                    to_be_mapped -= mapped_rate
                    interfaces_u[interface_u_highest_rate] -= mapped_rate
                    interfaces_v[interface_v_highest_rate] -= mapped_rate
        return cls(logical, physical, res_node_mapping, res_link_mapping_multiple_interfaces)

    def __str__(self):
        return "\n".join(
            [f"logical node {logical_node} mapped on physical node {physical_node}" for logical_node, physical_node in
             self.res_node_mapping.items()]) + "\n" + "\n".join(
            [f"logical link {logical_link} mapped on physical path {str(physical_path)}" for logical_link, physical_path
             in self.res_link_mapping.items()])
