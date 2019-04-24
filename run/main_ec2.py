from distriopt.packing import CloudInstance
from distriopt.packing.algorithms import PackGreedy
from distriopt import VirtualNetwork
from distriopt import SolutionStatus
import logging.config

if __name__ == '__main__':

    logging.config.fileConfig("/Users/andrea/Documents/GitHub/mapping_distrinet/logging.conf")

    logger = logging.getLogger()

    instance_ec2 = CloudInstance.get_ec2_instances()

    virtual = VirtualNetwork.create_random_nw(20)

    prob = PackGreedy(virtual, instance_ec2)
    time_solution, status = prob.solve()

    if SolutionStatus[status] == "Not Solved":
        print("Failed to solve")
    elif SolutionStatus[status] == "Unfeasible":
        print("Unfeasible Problem")
    else:
        pass
        # print(prob.solution)
    #print(prob.solution)
    print(prob.solution.cost)
    print(prob.solution.nodes_assignment[1])
    print(prob.solution.vm_used)
    print(prob.solution)