import pulp
import pytest


@pytest.fixture
def ilp():
    """Generate a Simple ILP."""
    prob = pulp.LpProblem("Example", pulp.LpMinimize)
    x1 = pulp.LpVariable("x1", 0, 10, pulp.LpInteger)
    x2 = pulp.LpVariable("x2", 5, 10, pulp.LpInteger)
    prob += x1 + x2, "obj"
    prob += x1 + x2 <= 6, "c1"
    return prob


class TestSolver(object):
    """Test Installed Solvers."""

    def test_glpk(self, ilp):
        try:
            ilp.solve(pulp.GLPK())
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"GLPK not installed")

    def test_cbc(self, ilp):
        try:
            ilp.solve(pulp.COIN())
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"Solver not installed")

    def test_cplex(self, ilp):
        try:
            ilp.solve(pulp.CPLEX_PY())
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"Solver not installed")

    def test_gurobi(self, ilp):
        try:
            ilp.solve(pulp.GUROBI())
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"Solver not installed")

    def test_scip(self, ilp):
        try:
            ilp.solve(pulp.SCIP())
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"Solver not installed")


a = 1
