from mininet.topo import Topo

import embedding as emb
from embedding.grid5000 import EmbedILP, EmbedPartition, EmbedMove, EmbedKbalanced
from embedding.grid5000 import PhysicalNetwork
from embedding.virtual import VirtualNetwork

if __name__ == '__main__':

    # create the physical network representation
    physical_topo = PhysicalNetwork.grid5000("grisou", group_interfaces=False)

    """
    Custom Network Example (for the moment fat tree and random are available on virtual.py
    """

    # custom VirtualNetwork
    virtual_topo = VirtualNetwork.create_fat_tree(k=10, density=2)

    prob = EmbedMove(virtual_topo, physical_topo)
    time_solution, status = prob.place()

    if emb.EmbedStatus[status] == "Not Solved":
        print("Failed to solve")
    elif emb.EmbedStatus[status] == "Unfeasible":
        print("Unfeasible Problem")
    else:
        pass
        # print(prob.solution)

    """
    Mininet Example
    """
    mn_topo = Topo()

    # Add Nodes
    leftHost = mn_topo.addHost('h1', cores=23, memory=8000)
    rightHost = mn_topo.addHost('h2', cores=23, memory=8000)
    leftSwitch = mn_topo.addSwitch('s3', cores=23, memory=8000)
    rightSwitch = mn_topo.addSwitch('s4', cores=23, memory=8000)

    # Add links
    mn_topo.addLink(leftHost, leftSwitch, rate=200)
    mn_topo.addLink(leftSwitch, rightSwitch, rate=200)
    mn_topo.addLink(rightSwitch, rightHost, rate=200)

    prob = EmbedMove(mn_topo, physical_topo)
    time_solution, status = prob.place()

    if emb.EmbedStatus[status] == "Not Solved":
        print("Failed to solve")
    elif emb.EmbedStatus[status] == "Unfeasible":
        print("Unfeasible Problem")
    else:
        pass
        #print(prob.solution)


    # Example: query the solution

    # nodes
    for u in mn_topo.nodes():
        print(f"{u} mapped on {prob.solution.node_info(u)}")

    # links
    for (u,v) in mn_topo.links():
        print(f"virtual link {(u,v)}")
        if prob.solution.node_info(u) != prob.solution.node_info(v):
            for path in prob.solution.link_info((u,v)):
                print(path)
        else:
            print("Nodes are on the same physical machine")