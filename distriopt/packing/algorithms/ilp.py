import logging
from collections import defaultdict

import pulp

from distriopt.constants import *
from distriopt.decorators import timeit
from distriopt.packing import PackingSolver
from distriopt.packing.solution import Solution

_log = logging.getLogger(__name__)


class PackILP(PackingSolver):
    @staticmethod
    def _get_solver(solver_name, timelimit):
        if solver_name == "cplex":
            return pulp.CPLEX_PY(msg=0, timeLimit=timelimit)
        elif solver_name == "gurobi":
            return pulp.GUROBI(msg=0, timeLimit=timelimit)
        elif solver_name == "glpk":
            return pulp.GLPK(msg=0, options=["--tmlim", str(timelimit)])
        elif solver_name == "cbc":
            return pulp.COIN(msg=0, maxSeconds=timelimit)
        elif solver_name == "scip":
            return pulp.SCIP(msg=0, options=["-c", f"set limits time {timelimit}"])
        else:
            raise ValueError("Invalid _get_solver name")

    @timeit
    def solve(self, **kwargs):

        solver_name = kwargs.get("solver", "cplex").lower()
        timelimit = int(kwargs.get("timelimit", "3600"))
        _log.info(f"called solve with the following parameters: {kwargs}")
        # UB on the number of instances of a certain type
        instances_UB = {
            vm_type: self._get_ub(vm_type) for vm_type in self.physical.vm_options
        }
        # instances on which a virtual node u may be placed
        feasible_instances = {
            u: self._get_feasible_instances(u) for u in self.virtual.nodes()
        }

        vm_used = pulp.LpVariable.dicts(
            "vm_used",
            (
                (vm_type, vm_id)
                for vm_type in self.physical.vm_options
                for vm_id in range(instances_UB[vm_type])
            ),
            cat=pulp.LpBinary,
        )
        node_mapping = pulp.LpVariable.dicts(
            "node_mapping",
            (
                (u, vm_type, vm_id)
                for u in self.virtual.nodes()
                for vm_type in feasible_instances[u]
                for vm_id in range(instances_UB[vm_type])
            ),
            cat=pulp.LpBinary,
        )
        # problem definition
        mapping_ILP = pulp.LpProblem("Packing ILP", pulp.LpMinimize)

        # objective function
        mapping_ILP += pulp.lpSum(
            (
                self.physical.hourly_cost(vm_type) * vm_used[(vm_type, vm_id)]
                for (vm_type, vm_id) in vm_used
            )
        )

        # Assignment of a virtual node to an EC2 instance
        for u in self.virtual.nodes():
            mapping_ILP += (
                pulp.lpSum(
                    (
                        node_mapping[(u, vm_type, vm_id)]
                        for vm_type in feasible_instances[u]
                        for vm_id in range(instances_UB[vm_type])
                    )
                )
                == 1,
                f"assignment of node {u}",
            )

        for (vm_type, vm_id) in vm_used:
            # CPU cores capacity constraints
            mapping_ILP += (
                pulp.lpSum(
                    (
                        self.virtual.req_cores(u) * node_mapping[(u, vm_type, vm_id)]
                        for u in self.virtual.nodes()
                        if vm_type in feasible_instances[u]
                    )
                )
                <= self.physical.cores(vm_type) * vm_used[vm_type, vm_id],
                f"core capacity of instance {vm_type, vm_id}",
            )
            # memory capacity constraints
            mapping_ILP += (
                pulp.lpSum(
                    (
                        self.virtual.req_memory(u) * node_mapping[(u, vm_type, vm_id)]
                        for u in self.virtual.nodes()
                        if vm_type in feasible_instances[u]
                    )
                )
                <= self.physical.memory(vm_type) * vm_used[vm_type, vm_id],
                f"memory capacity of instance {vm_type, vm_id}",
            )

        solver = self._get_solver(solver_name, timelimit)
        mapping_ILP.setSolver(solver)

        # solve the ILP
        status = pulp.LpStatus[mapping_ILP.solve()]
        obj_value = pulp.value(mapping_ILP.objective)

        if status == "Infeasible":
            self.status = Infeasible
            return Infeasible
        elif (status == "Not Solved" or status == "Undefined") and (
            not obj_value
            or sum(
                round(node_mapping[(u, vm_type, vm_id)].varValue)
                for (u, vm_type, vm_id) in node_mapping
            )
            != self.virtual.number_of_nodes()
        ):
            self.status = NotSolved
            return NotSolved

        if solver_name == "cplex":
            self.current_val = round(
                solver.solverModel.solution.MIP.get_best_objective(), 2
            )
        elif solver_name == "gurobi":
            self.current_val = round(mapping_ILP.solverModel.ObjBound, 2)
        else:
            self.current_val = 0

        assignment_ec2_instances = self.build_ILP_solution(node_mapping)
        self.solution = Solution.build_solution(
            self.virtual, self.physical, assignment_ec2_instances
        )
        self.status = Solved
        return Solved

    @staticmethod
    def build_ILP_solution(node_mapping):
        """Build an assignment of virtual nodes and virtual links starting from the values of the variables in the ILP."""

        # dict: key = vm_type, value = list of assigned virtual nodes
        assignment_ec2_instances = defaultdict(list)
        # dict: key = virtual node, value = vm assigned
        nodes_assignment = defaultdict()
        for (u, vm_type, vm_id) in node_mapping:
            # print(node_mapping[(u, vm_type, vm_id)],node_mapping[(u, vm_type, vm_id)].varValue)
            if round(node_mapping[(u, vm_type, vm_id)].varValue) == 1:
                assignment_ec2_instances[(vm_type, vm_id)].append(u)
                # nodes_assignment[u] = (vm_type, vm_id)
        return assignment_ec2_instances
