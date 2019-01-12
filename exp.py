"""
Experiments
"""
import logging.config

from definitions import *
from embedding import EmbedILP
from exceptions import TimeLimitError
from logical import LogicalNetwork
from physical import PhysicalNetwork


def time_comparison():
    try:
        os.remove("log.log")
    except:
        pass

    logging.config.fileConfig(os.path.join(basedir, 'logging.conf'), disable_existing_loggers=False)

    physical_topo = PhysicalNetwork.grid5000("grisou")


    for k in range(2, 13, 2):
        for group_interfaces in (True, False):
            virtual_topo = LogicalNetwork.create_fat_tree(k=k, density=int(k / 2))
            print(
                f"\n\n{k}-ary fat-tree has {len(virtual_topo.g.nodes())} nodes and {len(virtual_topo.g.edges())} edges")

            for solver in ["cplex", "gurobi", "glpk", "cbc"]:
                try:
                    time_solution, (value_solution, solution) = EmbedILP(virtual_topo, physical_topo)(solver=solver,
                                                                                                      obj="min_n_machines",
                                                                                                      timelimit=30,
                                                                                                      group_interfaces=group_interfaces)
                    solution.verify_solution(virtual_topo.g, physical_topo.g)
                    print(group_interfaces, solver, k, time_solution, value_solution)
                    print(solution, end="\n\n\n")

                except TimeLimitError:
                    print(solver, "a feasible solution has not been found")


if __name__ == "__main__":
    time_comparison()
