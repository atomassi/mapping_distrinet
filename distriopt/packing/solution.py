import itertools
import logging
from collections import Counter

from distriopt.constants import AssignmentError, NodeResourceError

_log = logging.getLogger(__name__)


class Solution(object):
    """Represent the output of the placement mapping.

    Examples
    --------
    >>> solution.node_info(u)
    ('t3.2xlarge', 1)
    >>> solution.node_info(v)
    ('t3.2xlarge', 2)
    >>> solution.vm_used((u,v))
    Counter({'t3.2xlarge': 5})
    >>> solution.cost
    1.89
    """

    def __init__(self, nodes_assignment, vm_used, cost):
        self.nodes_assignment = nodes_assignment
        self.vm_used = vm_used
        self.cost = cost

    def node_info(self, node):
        """Return the physical node where the virtual node has been placed."""
        return self.nodes_assignment[node]

    def output(self):
        raise NotImplementedError

    @staticmethod
    def verify_solution(virtual, physical, assignment_ec2_instances):
        """check if the solution is correct."""

        # every node is mapped
        nodes_assigned = set(itertools.chain(*assignment_ec2_instances.values()))
        if len(nodes_assigned) != len(virtual.nodes()):
            not_assigned_nodes = virtual.nodes() - nodes_assigned
            raise AssignmentError(
                f"{not_assigned_nodes} have not been assigned to any physical node"
            )
        # EC2 instance resources are not exceeded
        for vm_type, vm_id in assignment_ec2_instances:
            used_cores = sum(
                virtual.req_cores(u) for u in assignment_ec2_instances[(vm_type, vm_id)]
            )
            vm_cores = physical.cores(vm_type)
            used_memory = sum(
                virtual.req_memory(u)
                for u in assignment_ec2_instances[(vm_type, vm_id)]
            )
            vm_memory = physical.memory(vm_type)
            # cpu cores
            if used_cores > vm_cores:
                raise NodeResourceError("cpu cores exceeded")
            # memory
            elif used_memory > vm_memory:
                raise NodeResourceError("memory exceeded")

    @classmethod
    def build_solution(
        cls, virtual, physical, assignment_ec2_instances, check_solution=True
    ):
        if check_solution:
            Solution.verify_solution(virtual, physical, assignment_ec2_instances)

        nodes_assignment = {
            node: instance_id
            for instance_id in assignment_ec2_instances
            for node in assignment_ec2_instances[instance_id]
        }
        vm_used = Counter(vm_type for vm_type, _ in set(nodes_assignment.values()))
        cost = round(
            sum(
                physical.hourly_cost(vm_type) for vm_type, _ in assignment_ec2_instances
            ),
            2,
        )
        return cls(nodes_assignment, vm_used, cost)

    def __str__(self):
        res = f"hourly cost = {self.cost} €\n"
        res += f"machines used = {self.vm_used}\n"
        for node, (vm_type, vm_id) in self.nodes_assignment.items():
            res += f"{node} mapped on {vm_type} with id {vm_id}\n"

        return res
