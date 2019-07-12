"""
Experiments
"""
import logging.config
import os
import pickle
import pprint

from distriopt import SolutionStatus
from distriopt import VirtualNetwork
from distriopt.embedding import PhysicalNetwork
from distriopt.embedding.algorithms import EmbedGreedy, EmbedPartition, EmbedILP, EmbedBalanced
from distriopt.packing import CloudInstance
from distriopt.packing.algorithms import PackGreedy, PackILP, BestFitDopProduct, FirstFitDecreasingPriority, \
    FirstFitOrderedDeviation

try:
    os.remove("log.log")
except:
    pass

logging.config.fileConfig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf'),
                          disable_existing_loggers=False)
log = logging.getLogger(__name__)


def time_comparison_EC2(timelimit, min_nodes=25, max_nodes=500, step_size=25):
    instance_ec2 = CloudInstance.read_ec2_instances()

    solvers_ilp = {"cplex"}
    solvers_heu = {'greedy': PackGreedy, 'bfdp': BestFitDopProduct, 'ffdp': FirstFitDecreasingPriority,
                   'ffod': FirstFitOrderedDeviation}

    res_experiments = {'x': [], 'time': {}, 'value': {}}
    for method_name in solvers_ilp | set(solvers_heu.keys()):
        res_experiments['time'][method_name] = {}
        res_experiments['value'][method_name] = {}

    for n_nodes in range(min_nodes, max_nodes + 1, step_size):

        res_experiments['x'].append(n_nodes)

        virtual = VirtualNetwork.create_random_EC2(n_nodes)

        # ILP solver
        prob = PackILP(virtual, instance_ec2)

        for solver_name in solvers_ilp:

            time_solution, status = prob.solve(solver_name=solver_name, timelimit=timelimit)

            if SolutionStatus[status] != "Not Solved":
                res_experiments['time'][solver_name][n_nodes] = time_solution
                res_experiments['value'][solver_name][n_nodes] = prob.current_val
            else:
                res_experiments['time'][solver_name][n_nodes] = time_solution
                res_experiments['value'][solver_name][n_nodes] = prob.solution.cost

        # Heuristic approaches
        for heu in solvers_heu:
            prob = solvers_heu[heu](virtual, instance_ec2)
            time_solution, status = prob.solve()

            if SolutionStatus[status] == "Not Solved":
                print("Failed to solve")
                exit("failure")
            elif SolutionStatus[status] == "Unfeasible":
                print("Unfeasible Problem")
                exit("unfeasible")
            else:
                pass

            res_experiments['time'][heu][n_nodes] = time_solution
            res_experiments['value'][heu][n_nodes] = prob.solution.cost

        pprint.pprint(res_experiments)

        with open(os.path.join("results", f'res_ec2_{timelimit}s.pickle'), 'wb') as res_file:
            pickle.dump(res_experiments, res_file, protocol=pickle.HIGHEST_PROTOCOL)


def time_comparison_grid5000(timelimit, net_type='fat-tree'):
    """
    Custom Network  (for the moment fat tree and random are available on virtual.py)
    """
    # create the physical network representation
    physical = PhysicalNetwork.from_files("grisou")

    solvers_ilp = {"cplex"}
    solvers_heu = {'greedy': EmbedGreedy, 'k-balanced': EmbedBalanced, 'DivideSwap': EmbedPartition}

    res_experiments = {'x': [], 'time': {}, 'value': {}}
    for method_name in solvers_ilp | set(solvers_heu.keys()):
        res_experiments['time'][method_name] = {}
        res_experiments['value'][method_name] = {}

    if net_type == 'fat-tree':
        min_v = 2
        max_v = 12
        step_size = 2
    else:
        min_v = 25
        max_v = 175
        step_size = 25

    for v in range(min_v, max_v + 1, step_size):

        res_experiments['x'].append(v)

        if net_type == 'fat-tree':
            virtual = VirtualNetwork.create_fat_tree(v)
        else:
            virtual = VirtualNetwork.create_random_nw(v)

        # ILP solver
        prob = EmbedILP(virtual, physical)

        for solver_name in solvers_ilp:

            time_solution, status = prob.solve(solver_name=solver_name, timelimit=timelimit)

            if SolutionStatus[status] != "Solved":
                res_experiments['time'][solver_name][v] = time_solution
                res_experiments['value'][solver_name][v] = prob.current_val
            else:
                res_experiments['time'][solver_name][v] = time_solution
                res_experiments['value'][solver_name][v] = prob.solution.n_machines_used

        # Heuristic approaches
        for heu in solvers_heu:
            prob = solvers_heu[heu](virtual, physical)
            time_solution, status = prob.solve()

            if SolutionStatus[status] == "Not Solved":
                print("Failed to solve")
                exit("failure")
            elif SolutionStatus[status] == "Unfeasible":
                print("Unfeasible Problem")
                exit("unfeasible")
            else:
                pass

            res_experiments['time'][heu][v] = time_solution
            res_experiments['value'][heu][v] = prob.solution.n_machines_used

        pprint.pprint(res_experiments)

        with open(os.path.join("results", f'res_{net_type}_{timelimit}s.pickle'), 'wb') as res_file:
            pickle.dump(res_experiments, res_file, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    # time_comparison_EC2(timelimit=60)
    time_comparison_grid5000(timelimit=60, net_type='fat-tree')
    time_comparison_grid5000(timelimit=60, net_type='random')
