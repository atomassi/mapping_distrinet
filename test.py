import unittest
import warnings

import pulp


class TestInstalledSolvers(unittest.TestCase):
    def setUp(self):
        self.test_ILP = pulp.LpProblem("test", pulp.LpMinimize)
        dummy = pulp.LpVariable("dummy", lowBound=0, upBound=1)
        self.test_ILP += dummy <= 5
        warnings.simplefilter("ignore")

    def test_Cplex(self):
        self.test_ILP.setSolver(pulp.CPLEX(msg=0))
        self.test_ILP.solve()

    def test_Gurobi(self):
        self.test_ILP.setSolver(pulp.GUROBI(msg=0))
        self.test_ILP.solve()

    def test_GLPK(self):
        self.test_ILP.setSolver(pulp.GLPK(msg=0))
        self.test_ILP.solve()

    def test_CBC(self):
        self.test_ILP.setSolver(pulp.COIN(msg=0))
        self.test_ILP.solve()

    def test_Scip(self):
        self.test_ILP.setSolver(pulp.SCIP(msg=0))
        self.test_ILP.solve()


@unittest.skip("Not implemented")
class TestSolution(unittest.TestCase):
    def test_empty_solution(self):
        pass

    def test_valid_solution(self):
        pass

    def test_resources_node_bw_exceeded(self):
        pass

    def test_resources_node_cores_exceeded(self):
        pass

    def test_resources_link_exceeded(self):
        pass

    def test_invalid_mapping(self):
        pass


@unittest.skip("Not implemented")
class TestProblemInstances(unittest.TestCase):
    def test_unfeasible_1(self):
        pass

    def test_unfeasible_2(self):
        pass

    def test_unfeasible_3(self):
        pass

    def test_unfeasible_4(self):
        pass

    def test_unfeasible_5(self):
        pass

    def test_feasible_1(self):
        pass

    def test_feasible_2(self):
        pass

    def test_feasible_3(self):
        pass

    def test_feasible_4(self):
        pass

    def test_feasible_5(self):
        pass


if __name__ == "__main__":
    unittest.main()
