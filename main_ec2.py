from algorithms.packing import InstanceEC2
from algorithms.packing import PackHeu, PackILP
from algorithms.virtual import VirtualNetwork
from algorithms import SolutionStatus

if __name__ == '__main__':

    instance_ec2 = InstanceEC2.get_EC2_vritual_machines()

    virtual = VirtualNetwork.create_random_nw(20)

    prob = PackILP(virtual, instance_ec2)
    time_solution, status = prob.place()

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



