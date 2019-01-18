"""
Experiments
"""
import logging.config
import os
import pickle

from embedding.ec2 import EmbdedHeu_EC2
from embedding.ec2 import EmbedILP_EC2
from embedding.ec2 import InstanceEC2
from exceptions import TimeLimitError
from logical import LogicalNetwork

try:
    os.remove("log.log")
except:
    pass

logging.config.fileConfig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf'),
                          disable_existing_loggers=False)
log = logging.getLogger(__name__)


def time_comparison_EC2(timelimit, min_nodes=25, max_nodes=500, step_size=25):
    instance_ec2 = InstanceEC2.get_EC2_vritual_machines()

    solvers = ["cplex", "gurobi", "glpk", "cbc"]
    # to allow experiments to be interrupted and restarted later
    try:
        with open(f'res_{timelimit}s.pickle', 'rb') as res_file:
            res_experiments = pickle.load(res_file)
    except FileNotFoundError:
        res_experiments = {'time': {}, 'value': {}}
        for method_name in solvers:
            res_experiments['time'][method_name] = {}
            res_experiments['value'][method_name] = {}
        res_experiments['time']['heu'] = {}
        res_experiments['value']['heu'] = {}

    for n_nodes in range(min_nodes, max_nodes + 1, step_size):
        logical = LogicalNetwork.create_random_EC2(n_nodes)
        # To keep track of the solvers to be used.
        # If for a solver a feasible solution cannot be found for x nodes, then it is not used for x' > x nodes
        solvers_to_use = []
        # ILP solver
        for solver_name in solvers:
            try:
                time_solution, (value_solution, solution) = EmbedILP_EC2(logical, instance_ec2)(solver=solver_name,
                                                                                                timelimit=timelimit)
                solution.verify_solution()
                res_experiments['time'][solver_name][n_nodes] = time_solution
                res_experiments['value'][solver_name][n_nodes] = value_solution
                solvers_to_use.append(solver_name)

            except TimeLimitError:
                pass
        solvers = solvers_to_use

        # Heuristic approach
        time_solution, (value_solution, solution) = EmbdedHeu_EC2(logical, instance_ec2)()
        solution.verify_solution()
        res_experiments['time']['heu'][n_nodes] = time_solution
        res_experiments['value']['heu'][n_nodes] = value_solution
        with open(os.path.join("results", f'res_{timelimit}s.pickle'), 'wb') as res_file:
            pickle.dump(res_experiments, res_file, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":

    # time_comparison_EC2(timelimit=15)
    # time_comparison_EC2(timelimit=30)
    # time_comparison_EC2(timelimit=60)
    # time_comparison_EC2(timelimit=120)
    time_comparison_EC2(timelimit=300, min_nodes=100)
