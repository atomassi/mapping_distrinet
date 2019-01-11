import pulp

from exceptions import InfeasibleError
from .solve import Embed


class EmbedILP(Embed):
    @Embed.timeit
    def __call__(self, **kwargs):

        obj = kwargs.get('obj', 'no_obj')
        solver_ILP = kwargs.get('solver', 'cplex').lower()
        timelimit = int(kwargs.get('timelimit', '3600'))

        # link mapping variables
        f1 = lambda u, v, i, j, device: (u, v, i, j, device)
        f2 = lambda u, v, i, j, device: (u, v, j, i, device)
        link_mapping = pulp.LpVariable.dicts("link_mapping",
                                             [f(u, v, i, j, device) if u < v else f(v, u, i, j, device) for (u, v) in
                                              self.logical.edges() for (i, j, device) in self.physical.edges(keys=True)
                                              for f in [f1, f2]], cat=pulp.LpBinary)

        # node mapping variables
        node_mapping = pulp.LpVariable.dicts("node_mapping",
                                             [(u, i) for u in self.logical.nodes() for i in self.physical.nodes()],
                                             cat=pulp.LpBinary)

        # problem definition
        mapping_ILP = pulp.LpProblem("Mapping ILP", pulp.LpMinimize)

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

        # empty objective
        if obj == 'no_obj':
            mapping_ILP += pulp.LpVariable("dummy", lowBound=1, upBound=1)
        # minimize number of used machines
        elif obj == 'min_n_machines':
            usage_phy_machine = pulp.LpVariable.dicts("usage", [i for i in self.physical.nodes()], cat=pulp.LpBinary)

            mapping_ILP += pulp.lpSum(usage_phy_machine[i] for i in self.physical.nodes())

            for i in self.physical.nodes():
                for u in self.logical.nodes():
                    mapping_ILP += usage_phy_machine[i] >= node_mapping[(u, i)]
        # minimize used bandwidth
        elif obj == 'min_bw':
            mapping_ILP += pulp.lpSum(self.logical[u][v]['bw'] * (
                    link_mapping[u, v, i, j, device] + link_mapping[u, v, j, i, device]) if u < v else
                                      self.logical[u][v]['bw'] * (
                                              link_mapping[v, u, i, j, device] + link_mapping[v, u, j, i, device])
                                      for (u, v) in self.logical.edges() for (i, j, device) in
                                      self.physical.edges(keys=True))

        # Assignment of virtual nodes to physical nodes
        for u in self.logical.nodes():
            mapping_ILP += pulp.lpSum(node_mapping[(u, i)] for i in self.physical.nodes()) == 1

        for i in self.physical.nodes():
            # CPU limit
            mapping_ILP += pulp.lpSum(
                self.logical.nodes[u]['cpu_cores'] * node_mapping[(u, i)] for u in self.logical.nodes()) <= \
                           self.physical.nodes[i]['nb_cores']
            # Memory limit
            # mapping_ILP += pulp.lpSum(
            #    self.logical.nodes[u]['memory'] * node_mapping[(u, i)] for u in self.logical.nodes()) <= \
            #               self.physical.nodes[i]['ram_size']

        # Max latency for a logical link in the substrate network
        # @todo to be added

        # Bandwidth conservation
        # for each logical edge a flow conservation problem
        for (u, v) in self.logical.edges():
            (u, v) = (v, u) if u > v else (u, v)
            for i in self.physical.nodes():
                mapping_ILP += pulp.lpSum(
                    (link_mapping[(u, v, i, j, device)] - link_mapping[(u, v, j, i, device)]) for j in
                    self.physical.neighbors(i) for device in self.physical[i][j]) == (
                                       node_mapping[(u, i)] - node_mapping[(v, i)])

        # Link capacity
        for (i, j, device) in self.physical.edges(keys=True):
            mapping_ILP += pulp.lpSum(self.logical[u][v]['bw'] * (
                    link_mapping[u, v, i, j, device] + link_mapping[u, v, j, i, device]) if u < v else
                                      self.logical[u][v]['bw'] * (
                                              link_mapping[v, u, i, j, device] + link_mapping[v, u, j, i, device])
                                      for (u, v) in self.logical.edges()) <= self.physical[i][j][device]['rate']

        # given a logical link a physical machine the rate that goes out from the physical machine to an interface
        # or that comes in to the physical machine from an interface is at most 1
        for (u, v) in self.logical.edges():
            (u, v) = (v, u) if u > v else (u, v)
            for i in self.physical.nodes():
                mapping_ILP += pulp.lpSum(link_mapping[u, v, i, j, device] for j in self.physical.neighbors(i) for device in self.physical[i][j]) <= 1
                mapping_ILP += pulp.lpSum(link_mapping[u, v, j, i, device] for j in self.physical.neighbors(i) for device in self.physical[i][j]) <= 1

        # a link can be used only in a direction
        for (i, j, device) in self.physical.edges(keys=True):
            mapping_ILP += link_mapping[(u, v,i, j, device)] + link_mapping[(u,v, j,i, device)] <= 1

        status = mapping_ILP.solve()
        if pulp.LpStatus[status] == "Infeasible":
            raise InfeasibleError

        for logical_node in self.logical.nodes():
            for physical_node in self.physical.nodes():
                if node_mapping[(logical_node, physical_node)].varValue > 0:
                    self.res_node_mapping[logical_node] = physical_node

        for (u, v) in self.logical.edges():
            self.res_link_mapping[(u, v)] = {}
            for (i, j, device) in self.physical.edges(keys=True):
                flow_ratio_on_link = link_mapping[(u, v, i, j, device)].varValue + link_mapping[
                    (u, v, j, i, device)].varValue if u < v else link_mapping[(v, u, i, j, device)].varValue + \
                                                                 link_mapping[(v, u, j, i, device)].varValue
                if flow_ratio_on_link > 0:
                    self.res_link_mapping[(u, v)][(i, j, device)] = flow_ratio_on_link

        self.verify_solution()
        return pulp.value(mapping_ILP.objective), self.res_node_mapping, self.res_link_mapping
