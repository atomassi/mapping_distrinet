import itertools
import logging

import pulp

from distriopt.constants import *
from distriopt.decorators import timeit
from distriopt.embedding import EmbedSolver
from distriopt.embedding.solution import Solution

_log = logging.getLogger(__name__)


class EmbedILP(EmbedSolver):
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

        raise ValueError("Invalid Solver Name")

    @timeit
    def solve(self, **kwargs):

        obj = kwargs.get("obj", "min_n_machines")
        solver_name = kwargs.get("_get_solver", "glpk").lower()
        timelimit = int(kwargs.get("timelimit", "3600"))

        _log.debug(f"called ILP _get_solver with the following parameters: {kwargs}")

        # link mapping variables
        link_mapping = pulp.LpVariable.dicts(
            "link_mapping",
            itertools.chain(
                *(
                    ((u, v, i, j, device_id), (u, v, j, i, device_id))
                    for (u, v) in self.virtual.sorted_edges()
                    for (i, j, device_id) in self.physical.edges(keys=True)
                )
            ),
            lowBound=0,
            upBound=1,
            cat=pulp.LpContinuous
            if self.physical.grouped_interfaces
            else pulp.LpBinary,
        )

        # node mapping variables
        node_mapping = pulp.LpVariable.dicts(
            "node_mapping",
            ((u, i) for u in self.virtual.nodes() for i in self.physical.nodes()),
            cat=pulp.LpBinary,
        )

        # problem definition
        mapping_ILP = pulp.LpProblem("Mapping ILP", pulp.LpMinimize)
        # get _get_solver
        solver = self._get_solver(solver_name, timelimit)
        # set _get_solver
        mapping_ILP.setSolver(solver)

        # Case 1: empty objective
        if obj == "no_obj":
            mapping_ILP += pulp.LpVariable("dummy", lowBound=1, upBound=1)
        # Case 2: minimize number of used machines
        elif obj == "min_n_machines":
            # define variables to keep track of the number of machines used
            usage_phy_machine = pulp.LpVariable.dicts(
                "usage", [i for i in self.physical.nodes()], cat=pulp.LpBinary
            )
            # set objective
            mapping_ILP += pulp.lpSum(
                usage_phy_machine[i] for i in self.physical.nodes()
            )
            # a machine is used if at least a virtual node is mapped on it
            for i in self.physical.nodes():
                for u in self.virtual.nodes():
                    mapping_ILP += usage_phy_machine[i] >= node_mapping[(u, i)]
        # Case 3: minimize used bandwidth
        elif obj == "min_bw":
            mapping_ILP += pulp.lpSum(
                self.virtual.req_rate(u, v)
                * (
                    link_mapping[(u, v, i, j, device_id)]
                    + link_mapping[(u, v, j, i, device_id)]
                )
                for (u, v) in self.virtual.sorted_edges()
                for (i, j, device_id) in self.physical.edges(keys=True)
            )

        # Assignment of virtual nodes to physical nodes
        for u in self.virtual.nodes():
            mapping_ILP += (
                pulp.lpSum(node_mapping[(u, i)] for i in self.physical.nodes()) == 1,
                f"assignment of {u} to a physical node",
            )

        # Node capacity constraints
        for i in self.physical.nodes():
            # CPU limit
            mapping_ILP += (
                pulp.lpSum(
                    self.virtual.req_cores(u) * node_mapping[(u, i)]
                    for u in self.virtual.nodes()
                )
                <= self.physical.cores(i),
                f"CPU capacity for physical node {i}",
            )
            # Memory limit
            mapping_ILP += (
                pulp.lpSum(
                    self.virtual.req_memory(u) * node_mapping[(u, i)]
                    for u in self.virtual.nodes()
                )
                <= self.physical.memory(i),
                f"memory capacity for physical node {i}",
            )

        # Max latency for a virtual link in the substrate network
        # @todo to be added

        # Bandwidth conservation
        for (u, v) in self.virtual.sorted_edges():
            for i in self.physical.nodes():
                mapping_ILP += (
                    pulp.lpSum(
                        (
                            link_mapping[(u, v, i, j, device_id)]
                            - link_mapping[(u, v, j, i, device_id)]
                        )
                        for j in self.physical.neighbors(i)
                        for device_id in self.physical.interfaces_ids(i, j)
                    )
                    == (node_mapping[(u, i)] - node_mapping[(v, i)]),
                    f"flow conservation on physical node {i} for virtual link {u, v}",
                )

        # Link capacity
        for (i, j, device_id) in self.physical.edges(keys=True):
            mapping_ILP += (
                pulp.lpSum(
                    self.virtual.req_rate(u, v)
                    * (
                        link_mapping[(u, v, i, j, device_id)]
                        + link_mapping[(u, v, j, i, device_id)]
                    )
                    for (u, v) in self.virtual.sorted_edges()
                )
                <= self.physical.rate(i, j, device_id),
                f"link capacity for physical link {i, j, device_id}",
            )

        # Given a virtual link a physical machine the rate that goes out from the physical machine to an interface_name
        # or that comes in to the physical machine from an interface_name is at most 1
        for (u, v) in self.virtual.sorted_edges():
            for i in self.physical.nodes():
                mapping_ILP += (
                    pulp.lpSum(
                        link_mapping[(u, v, i, j, device_id)]
                        for j in self.physical.neighbors(i)
                        for device_id in self.physical.interfaces_ids(i, j)
                    )
                    <= 1,
                    f"virtual link {u, v} can use only a network interface_name to going out from physical node {i}",
                )
                mapping_ILP += (
                    pulp.lpSum(
                        link_mapping[(u, v, j, i, device_id)]
                        for j in self.physical.neighbors(i)
                        for device_id in self.physical.interfaces_ids(i, j)
                    )
                    <= 1,
                    f"virtual link {u, v} can use only a network interface_name to reach physical node {i}",
                )

        # A link can be used only in a direction
        for (u, v) in self.virtual.sorted_edges():
            for (i, j, device_id) in self.physical.edges(keys=True):
                mapping_ILP += (
                    link_mapping[(u, v, i, j, device_id)]
                    + link_mapping[(u, v, j, i, device_id)]
                    <= 1,
                    f"{u, v} can be mapped to a single direction of physical node {i, j, device_id}",
                )

        # solve the ILqP
        status = pulp.LpStatus[mapping_ILP.solve()]

        if solver_name == "cplex":
            self.current_val = solver.solverModel.solution.MIP.get_best_objective()
        elif solver_name == "gurobi":
            self.current_val = mapping_ILP.solverModel.ObjBound
        else:
            self.current_val = 0

        # check status
        if status == "Infeasible":
            self.status = Infeasible
            return Infeasible
        elif (status == "Not Solved" or status == "Undefined") and (
            not pulp.value(mapping_ILP.objective)
            or pulp.value(mapping_ILP.objective) < 1.1
        ):
            # @todo check specific _get_solver status
            self.status = NotSolved
            return NotSolved

        # build solution from variables values
        res_node_mapping, res_link_mapping = self._build_ILP_solution(
            self.virtual, self.physical, node_mapping, link_mapping
        )
        # if interfaces have been grouped, map to solution to the original network
        self.solution = Solution.build_solution(
            self.virtual, self.physical, res_node_mapping, res_link_mapping
        )
        self.status = Solved
        return Solved

    @staticmethod
    def _build_ILP_solution(virtual, physical, node_mapping, link_mapping):
        """Build an assignment of virtual nodes and virtual links starting from the values of the variables in the ILP
        """
        res_node_mapping = {}
        res_link_mapping = {}
        # mapping for the virtual nodes
        for virtual_node in virtual.nodes():
            res_node_mapping[virtual_node] = next(
                (
                    physical_node
                    for physical_node in physical.nodes()
                    if node_mapping[(virtual_node, physical_node)].varValue > 0
                ),
                None,
            )
        # mapping for the virtual links
        for (u, v) in virtual.sorted_edges():
            if res_node_mapping[u] != res_node_mapping[v]:
                s_node, d_node = res_node_mapping[u], res_node_mapping[v]
                # source of the virtual link
                source = next(
                    (
                        (s_node, device_id, j)
                        for j in physical.neighbors(s_node)
                        for device_id in physical.interfaces_ids(s_node, j)
                        if link_mapping[(u, v, s_node, j, device_id)].varValue
                        + link_mapping[(u, v, j, s_node, device_id)].varValue
                        > 0.99
                    ),
                    None,
                )
                # destination of the virtual link
                dest = next(
                    (
                        (j, device_id, d_node)
                        for j in physical.neighbors(d_node)
                        for device_id in physical.interfaces_ids(d_node, j)
                        if link_mapping[(u, v, d_node, j, device_id)].varValue
                        + link_mapping[(u, v, j, d_node, device_id)].varValue
                        > 0.99
                    ),
                    None,
                )
                # intermediary nodes in the path
                # @todo - intemediate nodes may be in the wrong order -> build the full path
                inter = [
                    (i, device_id, j)
                    for (i, j, device_id) in physical.edges(keys=True)
                    if i not in (s_node, d_node)
                    and j not in (s_node, d_node)
                    and link_mapping[(u, v, i, j, device_id)].varValue
                    + link_mapping[(u, v, j, i, device_id)].varValue
                    > 0.99
                ]

                res_link_mapping[(u, v)] = [source] + inter + [dest]
        return res_node_mapping, res_link_mapping
