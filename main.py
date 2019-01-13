import logging.config

from definitions import *
from embedding.grid5000 import EmbedILP_grid5000
from embedding.grid5000 import PhysicalNetwork
from exceptions import TimeLimitError
from logical import LogicalNetwork

try:
    os.remove("log.log")
except:
    pass

if __name__ == "__main__":
    logging.config.fileConfig(os.path.join(basedir, 'logging.conf'), disable_existing_loggers=False)
    log = logging.getLogger(__name__)

    physical_topo = PhysicalNetwork.grid5000("grisou", group_interfaces=False)
    virtual_topo = LogicalNetwork.create_fat_tree(k=2, density=2)

    for solver in ["cplex", "glpk", "cbc", "scip", "gurobi"]:
        for group_interfaces in True, False:

            try:
                time_solution, (value_solution, solution) = EmbedILP_grid5000(virtual_topo, physical_topo)(
                    solver=solver,
                    obj="min_n_machines",
                    timelimit=30,
                    group_interfaces=group_interfaces)
                solution.verify_solution()
                print(solution, end="\n\n\n")

            except TimeLimitError:
                print(solver, "feasible solution not found")
