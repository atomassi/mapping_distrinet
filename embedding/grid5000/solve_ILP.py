import pulp

from embedding import Embed
from embedding.exceptions import InfeasibleError, TimeLimitError
from .solution import Solution


class EmbedILP(Embed):

    @staticmethod
    def solver(solver_name, timelimit):
        if solver_name == 'cplex':
            return pulp.CPLEX(msg=0, timeLimit=timelimit)
        elif solver_name == 'gurobi':
            return pulp.GUROBI(msg=0, timeLimit=timelimit)
        elif solver_name == "glpk":
            return pulp.GLPK(msg=0, options=["--tmlim", str(timelimit)])
        elif solver_name == 'cbc':
            return pulp.COIN(msg=0, maxSeconds=timelimit)
        elif solver_name == 'scip':
            return pulp.SCIP(msg=0, options=['-c', f'set limits time {timelimit}'])
        else:
            raise ValueError("Invalid solver name")

    @Embed.timeit
    def __call__(self, **kwargs):

        obj = kwargs.get('obj', 'no_obj')
        solver_name = kwargs.get('solver', 'cplex').lower()
        timelimit = int(kwargs.get('timelimit', '3600'))
        if __debug__:
            self._log.debug(f"called ILP solver with the following parameters: {kwargs}")

        # link mapping variables
        f1 = lambda u, v, i, j, device: (u, v, i, j, device)
        f2 = lambda u, v, i, j, device: (u, v, j, i, device)
        # each undirected link is considered in alphabetical order to be consistent with variable names
        sorted_logical_edges = self.logical.sorted_edges()

        # if traffic cannot be splitted over multiple interfaces, then the link assignment variables
        # have binary domain, otherwise this constraint can be relaxed
        link_mapping = pulp.LpVariable.dicts("link_mapping",
                                             [f(u, v, i, j, device) for (u, v) in
                                              sorted_logical_edges for (i, j, device) in self.physical.edges(keys=True)
                                              for f in [f1, f2]], lowBound=0, upBound=1,
                                             cat='Binary' if not self.physical.grouped_interfaces else 'Continuous')

        # node mapping variables
        node_mapping = pulp.LpVariable.dicts("node_mapping",
                                             [(u, i) for u in self.logical.nodes() for i in self.physical.nodes()],
                                             cat=pulp.LpBinary)

        # problem definition
        mapping_ILP = pulp.LpProblem("Mapping ILP", pulp.LpMinimize)

        # get solver
        solver = self.solver(solver_name, timelimit)
        # set solver
        mapping_ILP.setSolver(solver)

        # Case 1: empty objective
        if obj == 'no_obj':
            mapping_ILP += pulp.LpVariable("dummy", lowBound=1, upBound=1)
        # Case 2: minimize number of used machines
        elif obj == 'min_n_machines':
            # define variables to keep track of the number of machines used
            usage_phy_machine = pulp.LpVariable.dicts("usage", [i for i in self.physical.nodes()], cat=pulp.LpBinary)
            # set objective
            mapping_ILP += pulp.lpSum(usage_phy_machine[i] for i in self.physical.nodes())
            # a machine is used if at least a logical node is mapped on it
            for i in self.physical.nodes():
                for u in self.logical.nodes():
                    mapping_ILP += usage_phy_machine[i] >= node_mapping[(u, i)]

        # Case 3: minimize used bandwidth
        elif obj == 'min_bw':
            mapping_ILP += pulp.lpSum(self.logical.req_rate(u, v) * (
                    link_mapping[(u, v, i, j, device)] + link_mapping[(u, v, j, i, device)])
                                      for (u, v) in sorted_logical_edges for (i, j, device) in
                                      self.physical.edges(keys=True))

        # Assignment of virtual nodes to physical nodes
        for u in self.logical.nodes():
            mapping_ILP += pulp.lpSum(
                node_mapping[(u, i)] for i in self.physical.nodes()) == 1, f"assignment of {u} to a physical node"

        for i in self.physical.nodes():
            # CPU limit
            mapping_ILP += pulp.lpSum(
                self.logical.req_cores(u) * node_mapping[(u, i)] for u in self.logical.nodes()) <= \
                           self.physical.cores(i), f"CPU capacity for physical node {i}"
            # Memory limit
            mapping_ILP += pulp.lpSum(
                self.logical.req_memory(u) * node_mapping[(u, i)] for u in self.logical.nodes()) <= \
                           self.physical.memory(i), f"memory capacity for physical node {i}"

        # Max latency for a logical link in the substrate network
        # @todo to be added

        # Bandwidth conservation
        # for each logical edge a flow conservation problem
        for (u, v) in sorted_logical_edges:
            for i in self.physical.nodes():
                mapping_ILP += pulp.lpSum(
                    (link_mapping[(u, v, i, j, device)] - link_mapping[(u, v, j, i, device)]) for j in
                    self.physical.neighbors(i) for device in self.physical.nw_interfaces(i, j)) == (
                                       node_mapping[(u, i)] - node_mapping[
                                   (v, i)]), f"flow conservation on physical node {i} for logical link {u, v}"

        # Link capacity
        for (i, j, device) in self.physical.edges(keys=True):
            mapping_ILP += pulp.lpSum(self.logical.req_rate(u, v) * (
                    link_mapping[(u, v, i, j, device)] + link_mapping[(u, v, j, i, device)])
                                      for (u, v) in sorted_logical_edges) <= self.physical.rate(i, j,
                                                                                                device), f"link capacity for physical link {i, j, device}"
        # given a logical link a physical machine the rate that goes out from the physical machine to an interface
        # or that comes in to the physical machine from an interface is at most 1
        for (u, v) in sorted_logical_edges:
            for i in self.physical.nodes():
                mapping_ILP += pulp.lpSum(
                    link_mapping[(u, v, i, j, device)] for j in self.physical.neighbors(i) for device in
                    self.physical.nw_interfaces(i,
                                                j)) <= 1, f"logical link {u, v} can use only a network interface to going out from physical node {i}"
                mapping_ILP += pulp.lpSum(
                    link_mapping[(u, v, j, i, device)] for j in self.physical.neighbors(i) for device in
                    self.physical.nw_interfaces(i,
                                                j)) <= 1, f"logical link {u, v} can use only a network interface to reach physical node {i}"

        # a link can be used only in a direction
        for (u, v) in sorted_logical_edges:
            for (i, j, device) in self.physical.edges(keys=True):
                mapping_ILP += link_mapping[(u, v, i, j, device)] + link_mapping[(
                    u, v, j, i,
                    device)] <= 1, f"{u, v} can be mapped to a single direction of physical node {i, j, device}"

        # solve the ILP
        status = pulp.LpStatus[mapping_ILP.solve()]

        # check status
        if status == "Infeasible":
            raise InfeasibleError
        elif (status == 'Not Solved' or status == "Undefined") and (
                not pulp.value(mapping_ILP.objective) or pulp.value(mapping_ILP.objective) < 1.1):
            # @todo check specific solver status
            raise TimeLimitError
        self._log.info(f"The solution found uses {pulp.value(mapping_ILP.objective)} physical machines")

        # build solution from variables values
        res_node_mapping, res_link_mapping = self.build_ILP_solution(node_mapping, link_mapping)
        # if interfaces have been grouped, map to solution to the original network
        if self.physical.grouped_interfaces:
            solution = Solution.map_to_multiple_interfaces(self.logical, self.physical, res_node_mapping,
                                                           res_link_mapping)
        else:
            solution = Solution(self.logical, self.physical, res_node_mapping, res_link_mapping)

        if obj == "min_n_machines":
            return pulp.value(mapping_ILP.objective), solution
        else:
            n_used_machines = sum(next((1 for logical_node in self.logical.nodes() if
                                        node_mapping[(logical_node, physical_node)].varValue > 0), 0) for physical_node
                                  in self.physical.nodes())

            return n_used_machines, solution

    def build_ILP_solution(self, node_mapping, link_mapping):
        """Build an assignment of virtual nodes and virtual links starting from the values of the variables in the ILP
        """
        res_node_mapping = {}
        res_link_mapping = {}
        # mapping of the logical nodes
        for logical_node in self.logical.nodes():
            res_node_mapping[logical_node] = next((physical_node for physical_node in self.physical.nodes() if
                                                   node_mapping[(logical_node, physical_node)].varValue > 0), None)

        for (u, v) in self.logical.edges():
            sorted_logical_link = (u, v) if u < v else (v, u)
            if res_node_mapping[u] != res_node_mapping[v]:
                # mapping for the source of the logical link
                link_source = res_node_mapping[u]
                source = next(((link_source, device, j) for j in self.physical.neighbors(link_source) for device in
                               self.physical.nw_interfaces(link_source, j) if
                               link_mapping[(*sorted_logical_link, link_source, j, device)].varValue + link_mapping[
                                   (*sorted_logical_link, j, link_source, device)].varValue > 0.99), None)
                # mapping for the destination of the logical link
                link_dest = res_node_mapping[v]
                dest = next(((link_dest, device, j) for j in self.physical.neighbors(link_dest) for device in
                             self.physical.nw_interfaces(link_dest, j) if
                             link_mapping[(*sorted_logical_link, link_dest, j, device)].varValue + link_mapping[
                                 (*sorted_logical_link, j, link_dest, device)].varValue > 0.99), None)
                res_link_mapping[(u, v)] = [source + dest + (1.0,)]

        return res_node_mapping, res_link_mapping
