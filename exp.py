"""
Experiments
"""
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


def time_comparison():
    logging.config.fileConfig(os.path.join(basedir, 'logging.conf'), disable_existing_loggers=False)

    for k in range(2, 13, 2):
        for group_interfaces in (True, False):
            physical_topo = PhysicalNetwork.grid5000("grisou", group_interfaces=group_interfaces)
            virtual_topo = LogicalNetwork.create_fat_tree(k=k, density=int(k / 2))
            print(
                f"\n\n{k}-ary fat-tree has {len(virtual_topo.g.nodes())} nodes and {len(virtual_topo.g.edges())} edges")

            for solver in ["cplex", "gurobi", "glpk", "cbc"]:
                try:
                    time_solution, (value_solution, solution) = EmbedILP_grid5000(virtual_topo, physical_topo)(
                        solver=solver,
                        obj="min_n_machines",
                        timelimit=30)

                    solution.verify_solution()

                    print(group_interfaces, solver, k, time_solution, value_solution)
                    # print(solution, end="\n\n\n")

                except TimeLimitError:
                    print(solver, "a feasible solution has not been found")


if __name__ == "__main__":
    time_comparison()
