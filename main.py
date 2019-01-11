import logging.config

from definitions import *
from embedding import EmbedILP
from logical import LogicalNetwork
from physical import PhysicalNetwork

if __name__ == "__main__":
    logging.config.fileConfig(os.path.join(basedir, 'logging.conf'), disable_existing_loggers=False)
    log = logging.getLogger(__name__)

    physical_topo = PhysicalNetwork.grid5000("grisou")
    virtual_topo = LogicalNetwork.create_fat_tree(k=2, density=2)

    for solver in ["cplex", "glpk", "cbc", "scip", "gurobi"]:
        for group_interfaces in True,False:
            time_solution, solution = EmbedILP(virtual_topo, physical_topo)(solver=solver, obj="min_n_machines",
                                                                        timelimit=30, group_interfaces=group_interfaces)

        solution.verify_solution(virtual_topo.g, physical_topo.g)

        try:
            solution.verify_solution(virtual_topo.g, physical_topo.g)
            print(solution)
        except Exception as err:
            print(err)
            exit(1)
