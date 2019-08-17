import networkx as nx
import pytest

from distriopt import VirtualNetwork
from distriopt.constants import *
from distriopt.embedding import PhysicalNetwork
from distriopt.embedding.algorithms import (
    EmbedBalanced,
    EmbedILP,
    EmbedPartition,
    EmbedGreedy,
)


@pytest.fixture(scope="module")
def virtual_nw():
    g = nx.Graph()
    g.add_node("Node_0", cores=3, memory=3000)
    g.add_node("Node_1", cores=3, memory=3000)
    g.add_edge("Node_0", "Node_1", rate=20000)

    yield VirtualNetwork(g)


@pytest.mark.parametrize("algo", [EmbedGreedy, EmbedBalanced, EmbedILP, EmbedPartition])
class TestGroupInterfaces(object):
    """Test the group interface option for a physical node."""

    def test_unfesible(self, algo, virtual_nw):
        # unfeasible, not enough rate
        physical_topo = PhysicalNetwork.create_test_nw(
            cores=4, memory=4000, rate=10000, group_interfaces=False
        )

        prob = algo(virtual_nw, physical_topo)
        time_solution, status = prob.solve()
        assert status == Infeasible
        assert time_solution > 0

    def test_feasible(self, algo, virtual_nw):
        # feasible, only one solution is possible: 50% on each interface
        physical_topo = PhysicalNetwork.create_test_nw(
            cores=4, memory=4000, rate=10000, group_interfaces=True
        )

        prob = algo(virtual_nw, physical_topo)
        time_solution, status = prob.solve()

        assert status == Solved
        assert time_solution > 0

        solution = prob.solution

        assert solution.node_info("Node_0") != solution.node_info("Node_1")
        assert len(solution.path_info(("Node_0", "Node_1"))) == 2

        for path in solution.path_info(("Node_0", "Node_1")):
            assert path.f_rate == 0.5
            assert len(path.path) == 2

        for link_map in solution.link_info(("Node_0", "Node_1")):
            assert link_map.s_node == solution.node_info("Node_0")
            assert link_map.d_node == solution.node_info("Node_1")
