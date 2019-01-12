import math

import pulp

from exceptions import InfeasibleError, TimeLimitError
from solution import Solution
from .solve import Embed


class EmbedILP(Embed):

    @staticmethod
    def build_ILP_solution(logical, physical, node_mapping, link_mapping):
        """Build an assignment of virtual nodes and virtual links starting from the values of the variables in the ILP
        """
        res_node_mapping = {}
        res_link_mapping = {}
        # mapping of the logical nodes
        for logical_node in logical.nodes():
            res_node_mapping[logical_node] = next((physical_node for physical_node in physical.nodes() if
                                                   node_mapping[(logical_node, physical_node)].varValue > 0), None)

        for (u, v) in logical.edges():
            sorted_logical_link = (u, v) if u < v else (v, u)
            if res_node_mapping[u] != res_node_mapping[v]:
                # mapping for the source of the logical link
                link_source = res_node_mapping[u]
                source = next(((link_source, device, j) for j in physical[link_source] for device in
                               physical[link_source][j] if
                               link_mapping[(*sorted_logical_link, link_source, j, device)].varValue + link_mapping[
                                   (*sorted_logical_link, j, link_source, device)].varValue > 0.99), None)
                # mapping for the destination of the logical link
                link_dest = res_node_mapping[v]
                dest = next(((link_dest, device, j) for j in physical[link_dest] for device in
                             physical[link_source][j] if
                             link_mapping[(*sorted_logical_link, link_dest, j, device)].varValue + link_mapping[
                                 (*sorted_logical_link, j, link_dest, device)].varValue > 0.99), None)
                res_link_mapping[(u, v)] = [source + dest + (1.0,)]

        return res_node_mapping, res_link_mapping

    @Embed.timeit
    def __call__(self, **kwargs):

        group_interfaces = kwargs.get('group_interfaces', False)
        obj = kwargs.get('obj', 'no_obj')
        solver_ILP = kwargs.get('solver', 'cplex').lower()
        timelimit = int(kwargs.get('timelimit', '3600'))
        self._log.info(f"called solver ILP with the following parameters: {kwargs}")

        logical = self.logical_topo.g
        physical = self.physical_topo.group_interfaces() if group_interfaces else self.physical_topo.g

        # link mapping variables
        f1 = lambda u, v, i, j, device: (u, v, i, j, device)
        f2 = lambda u, v, i, j, device: (u, v, j, i, device)
        # each undirected link is considered in alphabetical order to be consinstent with variable names
        sorted_logical_edges = set((u, v) if u < v else (v, u) for (u, v) in logical.edges())

        # if traffic cannot be splitted over multiple interfaces, then the link assignment variables
        # have binary domain, otherwise this constraint can be relaxed
        link_mapping = pulp.LpVariable.dicts("link_mapping",
                                            [f(u, v, i, j, device) for (u, v) in
                                             sorted_logical_edges for (i, j, device) in physical.edges(keys=True)
                                             for f in [f1, f2]], lowBound=0, upBound=1, cat='Binary' if not group_interfaces else 'Continuous')


        # node mapping variables
        node_mapping = pulp.LpVariable.dicts("node_mapping",
                                             [(u, i) for u in logical.nodes() for i in physical.nodes()],
                                             cat=pulp.LpBinary)

        # problem definition
        mapping_ILP = pulp.LpProblem("Mapping ILP", pulp.LpMinimize)

        # set solver
        if solver_ILP == 'cplex':
            solver = pulp.CPLEX(msg=0, timeLimit=timelimit)
        elif solver_ILP == 'gurobi':
            solver = pulp.GUROBI(msg=0, timeLimit=timelimit)
        elif solver_ILP == "glpk":
            solver = pulp.GLPK(msg=0, options=["--tmlim", str(timelimit)])
        elif solver_ILP == 'cbc':
            solver = pulp.COIN(msg=0, maxSeconds=timelimit)
        elif solver_ILP == 'scip':
            solver = pulp.SCIP(msg=0, options=['-c', f'set limits time {timelimit}'])
        else:
            raise ValueError("Invalid solver name")

        mapping_ILP.setSolver(solver)

        # Case 1: empty objective
        if obj == 'no_obj':
            mapping_ILP += pulp.LpVariable("dummy", lowBound=1, upBound=1)
        # Case 2: minimize number of used machines
        elif obj == 'min_n_machines':
            # define variables to keep track of the number of machines used
            usage_phy_machine = pulp.LpVariable.dicts("usage", [i for i in physical.nodes()], cat=pulp.LpBinary)
            # set objective
            mapping_ILP += pulp.lpSum(usage_phy_machine[i] for i in physical.nodes())
            # a machine is used if at least a logical node is mapped on it
            for i in physical.nodes():
                for u in logical.nodes():
                    mapping_ILP += usage_phy_machine[i] >= node_mapping[(u, i)]

        # Case 3: minimize used bandwidth
        elif obj == 'min_bw':
            mapping_ILP += pulp.lpSum(logical[u][v]['bw'] * (
                    link_mapping[(u, v, i, j, device)] + link_mapping[(u, v, j, i, device)])
                                      for (u, v) in sorted_logical_edges for (i, j, device) in
                                      physical.edges(keys=True))

        # Assignment of virtual nodes to physical nodes
        for u in logical.nodes():
            mapping_ILP += pulp.lpSum(node_mapping[(u, i)] for i in physical.nodes()) == 1

        for i in physical.nodes():
            # CPU limit
            mapping_ILP += pulp.lpSum(
                logical.nodes[u]['cpu_cores'] * node_mapping[(u, i)] for u in logical.nodes()) <= \
                           physical.nodes[i]['nb_cores']
            # Memory limit
            mapping_ILP += pulp.lpSum(
                logical.nodes[u]['memory'] * node_mapping[(u, i)] for u in logical.nodes()) <= \
                           physical.nodes[i]['ram_size']

        # Max latency for a logical link in the substrate network
        # @todo to be added

        # Bandwidth conservation
        # for each logical edge a flow conservation problem
        for (u, v) in sorted_logical_edges:
            for i in physical.nodes():
                mapping_ILP += pulp.lpSum(
                    (link_mapping[(u, v, i, j, device)] - link_mapping[(u, v, j, i, device)]) for j in
                    physical[i] for device in physical[i][j]) == (
                                       node_mapping[(u, i)] - node_mapping[(v, i)])

        # Link capacity
        for (i, j, device) in physical.edges(keys=True):
            mapping_ILP += pulp.lpSum(logical[u][v]['bw'] * (
                    link_mapping[(u, v, i, j, device)] + link_mapping[(u, v, j, i, device)])
                                      for (u, v) in sorted_logical_edges) <= physical[i][j][device]['rate']

        # given a logical link a physical machine the rate that goes out from the physical machine to an interface
        # or that comes in to the physical machine from an interface is at most 1
        for (u, v) in sorted_logical_edges:
            for i in physical.nodes():
                mapping_ILP += pulp.lpSum(
                    link_mapping[(u, v, i, j, device)] for j in physical[i] for device in
                    physical[i][j]) <= 1
                mapping_ILP += pulp.lpSum(
                    link_mapping[(u, v, j, i, device)] for j in physical[i] for device in
                    physical[i][j]) <= 1

        # a link can be used only in a direction
        for (u, v) in sorted_logical_edges:
            for (i, j, device) in physical.edges(keys=True):
                mapping_ILP += link_mapping[(u, v, i, j, device)] + link_mapping[(u, v, j, i, device)] <= 1

        status = mapping_ILP.solve()
        print(pulp.LpStatus[status])
        print(pulp.value(mapping_ILP.objective))

        if pulp.LpStatus[status] == "Infeasible":
            raise InfeasibleError
        elif pulp.LpStatus[status] == 'Not Solved' or pulp.LpStatus[status] == "Undefined":
            max_cores_per_machine = max(physical.nodes[i]['nb_cores'] for i in physical.nodes())
            max_memory_per_machine = max(physical.nodes[i]['ram_size'] for i in physical.nodes())
            lowbound = math.ceil(
                max(sum([logical.nodes[u]['cpu_cores'] for u in logical.nodes()]) / float(max_cores_per_machine),
                    sum([logical.nodes[u]['memory'] for u in logical.nodes()]) / float(max_memory_per_machine)))
            if not pulp.value(mapping_ILP.objective) or pulp.value(mapping_ILP.objective) < lowbound:
                raise TimeLimitError
        self._log.info(f"The solution found uses {pulp.value(mapping_ILP.objective)} physical machines")

        res_node_mapping, res_link_mapping = self.build_ILP_solution(logical, physical, node_mapping, link_mapping)
        if group_interfaces:
            solution = Solution.map_to_multiple_interfaces(logical, physical, res_node_mapping, res_link_mapping)
        else:
            solution = Solution(res_node_mapping, res_link_mapping)
        return pulp.value(mapping_ILP.objective), solution
