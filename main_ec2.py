import mapping as mp
from mapping.packing import CloudInstance
from mapping.packing.algorithms import PackILP, PackGreedy
from mapping import VirtualNetwork


if __name__ == '__main__':

    instance_ec2 = CloudInstance.get_ec2_instances()

    virtual = VirtualNetwork.create_random_nw(20)

    prob = PackGreedy(virtual, instance_ec2)
    time_solution, status = prob.solve()

    if mp.SolutionStatus[status] == "Not Solved":
        print("Failed to solve")
    elif mp.SolutionStatus[status] == "Unfeasible":
        print("Unfeasible Problem")
    else:
        pass
        # print(prob.solution)
    #print(prob.solution)
    print(prob.solution.cost)
    print(prob.solution.nodes_assignment[1])
    print(prob.solution.vm_used)
    print(prob.solution)



