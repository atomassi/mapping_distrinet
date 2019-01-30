import itertools
import logging

from embedding.exceptions import AssignmentError, NodeResourceError


class Solution(object):
    def __init__(self, physical, virtual, assignment_ec2_instances):
        self.physical = physical
        self.virtual = virtual
        self.assignment_ec2_instances = assignment_ec2_instances
        self._log = logging.getLogger(__name__)

    def output(self):
        raise NotImplementedError

    def verify_solution(self):
        """check if the solution is correct
        """
        # every node is mapped
        nodes_assigned = set(itertools.chain(*self.assignment_ec2_instances.values()))
        if len(nodes_assigned) != len(self.virtual.nodes()):
            not_assigned_nodes = self.virtual.nodes() - nodes_assigned
            raise AssignmentError(not_assigned_nodes)
        # EC2 instance resources are not exceeded
        for vm_type, vm_id in self.assignment_ec2_instances:
            used_cores = sum(self.virtual.req_cores(u) for u in self.assignment_ec2_instances[(vm_type, vm_id)])
            vm_cores = self.physical.cores(vm_type)
            used_memory = sum(self.virtual.req_memory(u) for u in self.assignment_ec2_instances[(vm_type, vm_id)])
            vm_memory = self.physical.memory(vm_type)
            # cpu cores
            if used_cores > vm_cores:
                raise NodeResourceError(vm_type, "CPU cores", used_cores, vm_cores)
            # memory
            elif used_memory > vm_memory:
                raise NodeResourceError(vm_type, "memory", used_memory, vm_memory)

    def __str__(self):
        res = ""
        for vm_type, vm_id in self.assignment_ec2_instances:
            res += f"EC2 instance {vm_type} ({self.physical.cores(vm_type)} cores, {self.physical.memory(vm_type)} mem) runs virtual nodes:\t"
            for node in self.assignment_ec2_instances[(vm_type, vm_id)]:
                res += f"id: {node} (cores: {self.virtual.req_cores(node)}, memory: {self.virtual.req_memory(node)})\t"
            res += "\n"
        return res
