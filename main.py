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

    time_solution, (value, res_node_mapping, res_link_mapping) = EmbedILP(virtual_topo, physical_topo)(solver="cplex",
                                                                                                       obj="min_n_machines")
