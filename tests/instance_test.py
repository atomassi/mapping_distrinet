def test_file():
    """Test reading a physical network from a file."""

    from distriopt.embedding import PhysicalNetwork
    import networkx as nx

    physical = PhysicalNetwork.from_files("example1")
    assert len(physical.compute_nodes) == 2
    assert physical.number_of_nodes() == 3
    assert len(physical.edges()) == 2
    assert nx.is_connected(physical.g)
    for node in physical.compute_nodes:
        assert physical.cores(node) == 16
        assert physical.memory(node) == 64000
    for i, j, device in physical.edges(keys=True):
        assert physical.rate(i, j, device) == 1000


def test_file_multiple():
    """Test reading multiple physical networks from a file."""

    from distriopt.embedding import PhysicalNetwork
    import networkx as nx

    physical = PhysicalNetwork.from_files("example1", "example2")
    assert len(physical.compute_nodes) == 4
    assert physical.number_of_nodes() == 5
    assert len(physical.edges()) == 4
    assert nx.is_connected(physical.g)
    for node in physical.compute_nodes:
        assert physical.cores(node) == 16
        assert physical.memory(node) == 64000
    for i, j, device in physical.edges(keys=True):
        assert physical.rate(i, j, device) == 1000


def test_ec2():
    """Test reading a physical network EC2 from a file."""

    from distriopt.packing import CloudInstance

    cloud = CloudInstance.read_ec2_instances(vm_type="general_purpose")
    for instance_type in cloud.vm_options:
        assert cloud.memory(instance_type) > 0
        assert cloud.cores(instance_type) > 0
        assert cloud.hourly_cost(instance_type) > 0


def test_logical_fat_tree():
    """Test the creation of a logical fat tree network topology"""

    from distriopt import VirtualNetwork

    virtual = VirtualNetwork.create_fat_tree(
        k=4, density=2, req_cores=2, req_memory=8000, req_rate=200
    )
    assert virtual.number_of_nodes() == 36
    assert len(virtual.edges()) == 48
    for node in virtual.nodes():
        assert virtual.req_cores(node) == 2
        assert virtual.req_memory(node) == 8000
    for i, j in virtual.edges():
        assert virtual.req_rate(i, j) == 200


def test_logical_random():
    """Test the creation of a logical random network topology."""

    from distriopt import VirtualNetwork

    virtual = VirtualNetwork.create_random_nw(
        20, req_cores=2, req_memory=8000, req_rate=200
    )
    assert virtual.number_of_nodes() == 20
    for node in virtual.nodes():
        assert virtual.req_cores(node) == 2
        assert virtual.req_memory(node) == 8000
    for i, j in virtual.edges():
        assert virtual.req_rate(i, j) == 200


def test_logical_ec2():
    """Test the creation of a logical EC2 random instance."""

    from distriopt import VirtualNetwork

    virtual = VirtualNetwork.create_random_EC2(n_nodes=10)
    for node in virtual.nodes():
        assert virtual.req_cores(node) in range(1, 9)
        assert virtual.req_memory(node) in [512] + list(range(1024, 8193, 1024))


def test_mininet_conversion_to_logical():
    """Test the conversion from a mininet logical network to a logical one."""

    import networkx as nx
    from distriopt import VirtualNetwork
    from mininet.topo import Topo

    virt_topo_mn = Topo()

    # Add nodes
    u = virt_topo_mn.addHost("u", cores=2, memory=1000)
    v = virt_topo_mn.addHost("v", cores=2, memory=1000)
    z = virt_topo_mn.addSwitch("z", cores=2, memory=1000)
    # Add links
    virt_topo_mn.addLink(u, v, rate=1000)
    virt_topo_mn.addLink(v, z, rate=1000)
    virt_topo_mn.addLink(u, z, rate=1000)

    virtual_topo = VirtualNetwork.from_mininet(virt_topo_mn)

    assert virtual_topo.number_of_nodes() == 3
    assert len(virtual_topo.edges()) == 3
    assert nx.is_connected(virtual_topo.g)

    for node in virtual_topo.nodes():
        assert virtual_topo.req_cores(node) == 2
        assert virtual_topo.req_memory(node) == 1000
    for i, j in virtual_topo.edges():
        assert virtual_topo.req_rate(i, j) == 1000


def test_mininet_conversion_to_physical():
    """Test the conversion from a mininet physical network to a PhysicalNetwork one."""

    import networkx as nx
    from distriopt.embedding import PhysicalNetwork
    from mininet.topo import Topo

    phy_topo_mn = Topo()

    # Add nodes
    master1 = phy_topo_mn.addHost("Master1", cores=2, memory=1000)
    node1 = phy_topo_mn.addHost("Node1", cores=2, memory=1000)
    sw = phy_topo_mn.addSwitch("SW")
    # Add links
    phy_topo_mn.addLink(master1, sw, port1="eth0", port2="eth0", rate=1000)
    phy_topo_mn.addLink(master1, sw, port1="eth1", port2="eth2", rate=1000)
    phy_topo_mn.addLink(node1, sw, port1="eth0", port2="eth1", rate=1000)

    phy_topo = PhysicalNetwork.from_mininet(phy_topo_mn)
    assert len(phy_topo.compute_nodes) == 2
    assert phy_topo.number_of_nodes() == 3
    assert len(phy_topo.edges()) == 3
    assert nx.is_connected(phy_topo.g)
    for node in phy_topo.compute_nodes:
        assert phy_topo.cores(node) == 2
        assert phy_topo.memory(node) == 1000
    for i, j, device in phy_topo.edges(keys=True):
        assert phy_topo.rate(i, j, device) == 1000
