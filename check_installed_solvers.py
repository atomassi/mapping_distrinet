import pulp
import pytest


@pytest.fixture
def ilp():
    """Generate a simple ILP with 5 as an optimal solution."""
    prob = pulp.LpProblem("Example", pulp.LpMinimize)
    x1 = pulp.LpVariable("x1", 0, 10, pulp.LpInteger)
    x2 = pulp.LpVariable("x2", 5, 10, pulp.LpInteger)
    prob += x1 + x2, "obj"
    prob += x1 + x2 <= 6, "c1"
    return prob


class TestSolver(object):
    """Test Installed Solvers."""

    def test_glpk(self, ilp):
        """Test method for GLPK."""
        try:
            ilp.solve(pulp.GLPK())
            assert round(pulp.value(ilp.objective), 0) == 5
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"Solver not installed")

    def test_cbc(self, ilp):
        """Test method for CBC."""
        try:
            ilp.solve(pulp.COIN())
            assert round(pulp.value(ilp.objective), 0) == 5
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"Solver not installed")

    def test_cplex(self, ilp):
        """Test method for CPLEX."""
        try:
            ilp.solve(pulp.CPLEX_PY())
            assert round(pulp.value(ilp.objective), 0) == 5
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"Solver not installed")

    def test_gurobi(self, ilp):
        """Test method for GUROBI."""
        try:
            ilp.solve(pulp.GUROBI())
            assert round(pulp.value(ilp.objective), 0) == 5
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"Solver not installed")

    def test_scip(self, ilp):
        """Test method for SCIP."""
        try:
            ilp.solve(pulp.SCIP())
            assert round(pulp.value(ilp.objective), 0) == 5
        except pulp.solvers.PulpSolverError:
            pytest.fail(f"Solver not installed")