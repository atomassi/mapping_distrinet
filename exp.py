"""
Experiments
"""
import logging.config
import os
import pickle

from embedding.ec2 import EmbdedHeu_EC2
from embedding.ec2 import EmbedILP_EC2
from embedding.ec2 import InstanceEC2
from embedding.grid5000 import EmbedILP_grid5000
from embedding.grid5000 import PhysicalNetwork
from exceptions import TimeLimitError
from logical import LogicalNetwork

try:
    os.remove("log.log")
except:
    pass

logging.config.fileConfig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf'),
                          disable_existing_loggers=False)
log = logging.getLogger(__name__)


def time_comparison_EC2():
    instance_ec2 = InstanceEC2.get_EC2_vritual_machines()
    # res_experiments = {'time': defaultdict(lambda: defaultdict(float)),
    #                   'value': defaultdict(lambda: defaultdict(float))}
    res_experiments = {'time': {}, 'value': {}}
    for method_name in ["cplex", "gurobi", "glpk", "cbc", "heu"]:
        res_experiments['time'][method_name] = {}
        res_experiments['value'][method_name] = {}

    for n_nodes in range(25, 501, 25):
        logical = LogicalNetwork.create_random_EC2(n_nodes)
        # ILP solver
        for solver_name in ["cplex", "gurobi", "glpk", "cbc"]:
            try:
                time_solution, (value_solution, solution) = EmbedILP_EC2(logical, instance_ec2)(solver=solver_name,
                                                                                                timelimit=30)
                solution.verify_solution()
                res_experiments['time'][solver_name][n_nodes] = time_solution
                res_experiments['value'][solver_name][n_nodes] = value_solution
            except TimeLimitError:
                pass

        # Heuristic approach
        time_solution, (value_solution, solution) = EmbdedHeu_EC2(logical, instance_ec2)()
        solution.verify_solution()
        res_experiments['time']['heu'][n_nodes] = time_solution
        res_experiments['value']['heu'][n_nodes] = value_solution
        with open('res.pickle', 'wb') as res_file:
            pickle.dump(res_experiments, res_file, protocol=pickle.HIGHEST_PROTOCOL)

if __name__ == "__main__":
    time_comparison_EC2()
    # time_comparison_grid5000()
