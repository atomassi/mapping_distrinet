from mininet.topo import Topo

import mapping as mp
from mapping import VirtualNetwork
from mapping.embedding import PhysicalNetwork
from mapping.embedding.algorithms import EmbedBalanced, EmbedPartition, EmbedTwoPhases, EmbedILP

if __name__ == '__main__':

    # create the physical network representation
    physical_topo = PhysicalNetwork.grid5000("grisou", group_interfaces=False)

    """
    Custom Network  (for the moment fat tree and random are available on virtual.py)
    """

    # custom VirtualNetwork
    virtual_topo = VirtualNetwork.create_fat_tree(k=10, density=2)

    prob = EmbedTwoPhases(virtual_topo, physical_topo)
    time_solution, status = prob.solve()

    if mp.SolutionStatus[status] == "Not Solved":
        print("Failed to solve")
    elif mp.SolutionStatus[status] == "Infeasible":
        print("Unfeasible Problem")
    else:
        pass
        # print(prob.solution)

    """
    Mininet Example - both virtual and physical are mininet Topo network
    """
    #### virtual mininet ####
    virtual_topo = Topo()

    # Add Nodes
    leftHost = virtual_topo.addHost('h1', cores=23, memory=8000)
    rightHost = virtual_topo.addHost('h2', cores=23, memory=8000)
    leftSwitch = virtual_topo.addSwitch('s3', cores=23, memory=8000)
    rightSwitch = virtual_topo.addSwitch('s4', cores=23, memory=8000)

    # Add links
    virtual_topo.addLink(leftHost, leftSwitch, rate=200)
    virtual_topo.addLink(leftSwitch, rightSwitch, rate=200)
    virtual_topo.addLink(rightSwitch, rightHost, rate=200)

    #### physical mininet ####

    phy_topo = Topo()

    # Add nodes
    master1 = phy_topo.addHost('Master1', cores=1000, memory=80000)
    node1 = phy_topo.addHost('Node1', cores=1000, memory=80000)
    sw = phy_topo.addSwitch('SW')

    # Add links
    phy_topo.addLink(master1, sw, nw_interfaces={"eth0": 1000})
    phy_topo.addLink(node1, sw, nw_interfaces={"eth0": 1000})

    prob = EmbedTwoPhases(virtual=virtual_topo, physical=phy_topo)
    time_solution, status = prob.solve()
    if mp.SolutionStatus[status] == "Not Solved":
        print("Failed to solve")
        exit(1)
    elif mp.SolutionStatus[status] == "Infeasible":
        print("Unfeasible Problem")
        exit(1)
    else:
        pass
        # print(prob.solution)

    #

    """
    Mininet Example - virtual is mininet Topo network and physical a PhysicalNetwork one
    """
    virtual_topo = Topo()

    # Add Nodes
    leftHost = virtual_topo.addHost('h1', cores=23, memory=8000)
    rightHost = virtual_topo.addHost('h2', cores=23, memory=8000)
    leftSwitch = virtual_topo.addSwitch('s3', cores=23, memory=8000)
    rightSwitch = virtual_topo.addSwitch('s4', cores=23, memory=8000)

    # Add links
    virtual_topo.addLink(leftHost, leftSwitch, rate=200)
    virtual_topo.addLink(leftSwitch, rightSwitch, rate=200)
    virtual_topo.addLink(rightSwitch, rightHost, rate=200)

    prob = EmbedTwoPhases(virtual=virtual_topo, physical=physical_topo)
    time_solution, status = prob.solve()
    if mp.SolutionStatus[status] == "Not Solved":
        print("Failed to solve")
        exit(1)
    elif mp.SolutionStatus[status] == "Infeasible":
        print("Unfeasible Problem")
        exit(1)
    else:
        pass

    # example: query the solution

    # nodes
    for u in virtual_topo.nodes():
        print(f"{u} mapped on {prob.solution.node_info(u)}")

    # links
    for (u, v) in virtual_topo.links():
        print(f"*** virtual link {(u, v)} mapped on")
        if prob.solution.node_info(u) != prob.solution.node_info(v):
            for path in prob.solution.link_info((u, v)):
                print(path)
        else:
            print("Nodes are on the same physical machine")

    """
    example output
    h1 mapped on grisou-3
    h2 mapped on grisou-16
    s3 mapped on grisou-12
    s4 mapped on grisou-32
    *** virtual link ('h1', 's3') mapped on
    source: grisou-3, source_device: eth0, destination node: grisou-12, destination device: eth0, rate to route: 1
    *** virtual link ('s3', 's4') mapped on
    source: grisou-12, source_device: eth1, destination node: grisou-32, destination device: eth0, rate to route: 1
    *** virtual link ('s4', 'h2') mapped on
    source: grisou-32, source_device: eth1, destination node: grisou-16, destination device: eth0, rate to route: 1
    """