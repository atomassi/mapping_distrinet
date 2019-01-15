from collections import defaultdict

import pulp

from exceptions import InfeasibleError, TimeLimitError
from .solution import Solution
from .solve import Embed


class EmbedILP(Embed):

    @staticmethod
    def solver(solver_name, timelimit):
        if solver_name == 'cplex':
            return pulp.CPLEX(msg=1, timeLimit=timelimit)
        elif solver_name == 'gurobi':
            return pulp.GUROBI(msg=1, timeLimit=timelimit)
        elif solver_name == "glpk":
            return pulp.GLPK(msg=1, options=["--tmlim", str(timelimit)])
        elif solver_name == 'cbc':
            return pulp.COIN(msg=1, maxSeconds=timelimit)
        elif solver_name == 'scip':
            return pulp.SCIP(msg=0, options=['-c', f'set limits time {timelimit}'])
        else:
            raise ValueError("Invalid solver name")

    def get_UB(self, vm_type):
        """Return an upper bound on the maximum number of EC2 instances of type vm_type neede to pack all the nodes
        """
        cpu_cores_instance, memory_instance = self.physical.get_cores(vm_type), self.physical.get_memory(vm_type)
        n_instances_needed = remaining_cpu_cores = remaining_memory = 0
        for u in self.logical.nodes():
            req_cores, req_memory = self.logical.requested_cores(u), self.logical.requested_memory(u)
            if req_cores <= remaining_cpu_cores and req_memory <= remaining_memory:
                remaining_cpu_cores -= req_cores
                remaining_memory -= req_memory
            elif req_cores <= cpu_cores_instance and req_memory <= memory_instance:
                remaining_cpu_cores = cpu_cores_instance - req_cores
                remaining_memory = memory_instance - req_memory
                n_instances_needed += 1
        return n_instances_needed

    @Embed.timeit
    def __call__(self, **kwargs):

        solver_name = kwargs.get('solver', 'cplex').lower()
        timelimit = int(kwargs.get('timelimit', '3600'))
        self._log.info(f"called ILP solver with the following parameters: {kwargs}")

        vm_used = pulp.LpVariable.dicts("vm_used",
                                        ((vm_type, vm_id) for vm_type in self.physical.vm_options for vm_id in
                                         range(self.get_UB(vm_type))), cat=pulp.LpBinary)
        node_mapping = pulp.LpVariable.dicts("node_mapping",
                                             ((u, vm_type, vm_id) for u in self.logical.nodes() for (vm_type, vm_id) in
                                              vm_used), cat=pulp.LpBinary)
        # problem definition
        mapping_ILP = pulp.LpProblem("Mapping ILP", pulp.LpMinimize)

        # objective function
        mapping_ILP += pulp.lpSum(
            (self.physical.get_hourly_cost(vm_type) * vm_used[(vm_type, vm_id)] for (vm_type, vm_id) in vm_used))

        # Assignment of a virtual node to an EC2 instance
        for u in self.logical.nodes():
            mapping_ILP += pulp.lpSum(
                (node_mapping[(u, vm_type, vm_id)] for (vm_type, vm_id) in vm_used)) >= 1, f"assignment of node {u}"

        for (vm_type, vm_id) in vm_used:
            # CPU cores capacity constraints
            mapping_ILP += pulp.lpSum(
                (self.logical.requested_cores(u) * node_mapping[(u, vm_type, vm_id)] for u in
                 self.logical.nodes())) <= self.physical.get_cores(vm_type) * \
                           vm_used[vm_type, vm_id], f"core capacity of instance {vm_type, vm_id}"
            # memory capacity constraints
            mapping_ILP += pulp.lpSum(
                (self.logical.requested_memory(u) * node_mapping[(u, vm_type, vm_id)] for u in
                 self.logical.nodes())) <= self.physical.get_memory(
                vm_type) * \
                           vm_used[vm_type, vm_id], f"memory capacity of instance {vm_type, vm_id}"

        solver = self.solver(solver_name, timelimit)
        # set solver
        mapping_ILP.setSolver(solver)

        # solve the ILP
        status = pulp.LpStatus[mapping_ILP.solve()]
        if status == "Infeasible":
            raise InfeasibleError
        elif (status == 'Not Solved' or status == "Undefined") and (
                not pulp.value(mapping_ILP.objective) or sum(node_mapping[(u, vm_type, vm_id)].varValue for (u, vm_type, vm_id) in node_mapping) == 0):
            raise TimeLimitError

        assignment_ec2_instances = self.build_ILP_solution(node_mapping)
        solution = Solution(self.physical, self.logical, assignment_ec2_instances)
        return round(pulp.value(mapping_ILP.objective),2), solution

    def build_ILP_solution(self, node_mapping):
        """Build an assignment of virtual nodes and virtual links starting from the values of the variables in the ILP
        """

        # dict: key = vm_type, value = list of assigned virtual nodes
        assignment_ec2_instances = defaultdict(list)
        # dict: key = virtual node, value = vm assigned
        assignment_nodes = defaultdict()
        for (u, vm_type, vm_id) in node_mapping:
            # print(node_mapping[(u, vm_type, vm_id)],node_mapping[(u, vm_type, vm_id)].varValue)
            if node_mapping[(u, vm_type, vm_id)].varValue > 0:
                assignment_ec2_instances[(vm_type, vm_id)].append(u)
                # assignment_nodes[u] = (vm_type, vm_id)
        return assignment_ec2_instances
