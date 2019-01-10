import logging.config

from definitions import *
from embedding import EmbedILP
from logical import LogicalNetwork
from physical import PhysicalNetwork

if __name__ == "__main__":

    logging.config.fileConfig(os.path.join(basedir, 'logging.conf'), disable_existing_loggers=False)
    log = logging.getLogger(__name__)

    physical_topo = PhysicalNetwork.grid5000("grisou")

    cplex_time = {}
    cplex_value = {}
    glpk_time = {}
    glpk_value = {}
    coin_time = {}
    coin_value = {}

    # obj = "min_bw"
    obj = "min_n_machines"
    # obj = "no_obj"

    for k in range(2, 9, 2):
        virtual_topo = LogicalNetwork.create_fat_tree(k=k, density=int(k / 2))
        time_solution, (value, res_node_mapping, res_link_mapping) = EmbedILP(virtual_topo, physical_topo)(
            solver="cplex", obj=obj)
        cplex_time[k] = time_solution
        cplex_value[k] = value
        time_solution, (value, res_node_mapping, res_link_mapping) = EmbedILP(virtual_topo, physical_topo)(
            solver="glpk", obj=obj)
        glpk_time[k] = time_solution
        glpk_value[k] = value
        time_solution, (value, res_node_mapping, res_link_mapping) = EmbedILP(virtual_topo, physical_topo)(
            solver="coin-or", obj=obj)
        coin_time[k] = time_solution
        coin_value[k] = value

        print(cplex_time, glpk_time, coin_time)
        print(cplex_value, glpk_value, coin_value)
