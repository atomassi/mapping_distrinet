import itertools
import logging

from exceptions import AssignmentError, NodeResourceError


class Solution(object):
    def __init__(self, physical, logical, assignment_ec2_instances):
        self.physical = physical
        self.logical = logical
        self.assignment_ec2_instances = assignment_ec2_instances
        self._log = logging.getLogger(__name__)

    def output(self):
        raise NotImplementedError

    def verify_solution(self):
        """check if the solution is correct
        """
        # every node is mapped
        nodes_assigned = set(itertools.chain(*self.assignment_ec2_instances.values()))
        if len(nodes_assigned) != len(self.logical.nodes()):
            not_assigned_nodes = self.logical.nodes() - nodes_assigned
            raise AssignmentError(not_assigned_nodes)
        # EC2 instance resources are not exceeded
        for vm_type, vm_id in self.assignment_ec2_instances:
            used_cores = sum(self.logical.requested_cores(u) for u in self.assignment_ec2_instances[(vm_type, vm_id)])
            vm_cores = self.physical.get_cores(vm_type)
            used_memory = sum(self.logical.requested_memory(u) for u in self.assignment_ec2_instances[(vm_type, vm_id)])
            vm_memory = self.physical.get_memory(vm_type)
            # cpu cores
            if used_cores > vm_cores:
                raise NodeResourceError(vm_type, "CPU cores", used_cores, vm_cores)
            # memory
            elif used_memory > vm_memory:
                raise NodeResourceError(vm_type, "memory", used_memory, vm_memory)

    def __str__(self):
        return "\n".join(
            [f"EC2 instance {vm_type} runs logical nodes "
             f"{', '.join(str(node) for node in self.assignment_ec2_instances[(vm_type, vm_id)])}" for vm_type, vm_id in
             self.assignment_ec2_instances])
