import pulp


def test_solvers():
    """test installed solvers
    """
    print("TESTING SOLVERS")
    solvers = {"Cplex": pulp.CPLEX, "GLPK": pulp.GLPK, "CBC": pulp.COIN, "Scip": pulp.SCIP, "Gurobi": pulp.GUROBI}
    # definition of a test problem
    test_ILP = pulp.LpProblem("test", pulp.LpMinimize)
    dummy = pulp.LpVariable("dummy", lowBound=1, upBound=10)
    test_ILP += dummy <= 5

    # check all the solver
    for solver_name, solver in solvers.items():
        print(f"testing {solver_name} ...", end="")
        try:
            test_ILP.setSolver(solver(msg=0))
            test_ILP.solve()
            print("OK")
        except pulp.PulpSolverError:
            print("Not found")


if __name__ == "__main__":
    test_solvers()
