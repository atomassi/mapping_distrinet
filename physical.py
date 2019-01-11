import json
import logging

import networkx as nx

from definitions import *


class PhysicalNetwork(object):

    def __init__(self, g):
        self.g = g
        self._log = logging.getLogger(__name__)

    @classmethod
    def grid5000(cls, name, n_interfaces_to_consider=float('inf')):
        """Import the physical network topology from a Grid5000 cluster.

        Parameters
        ----------
        name : the name of the cluster in grid5000 to be considered
            The corresponding filename should be placed in instances/physical/name.json

        n_interfaces_to_consider : the maximum number of network interfaces to be considered per node (optional, default: all)

        Returns
        -------
        an instance of the PhysicalNetwork class
        """
        g = nx.MultiGraph()

        # compute node
        with open(os.path.join(basedir, "instances", "physical", name + ".json")) as f:
            data = json.load(f)

            for node in data['items']:
                g.add_node(node['uid'], nb_cores=node['architecture']['nb_cores'] * node['architecture']['nb_procs'],
                           ram_size=node['main_memory']['ram_size'])

                n_added_interfaces = 0
                for interface, link in enumerate(node['network_adapters']):
                    if link['device'].startswith("eth") and link['enabled'] and link['driver'] == "ixgbe":
                        g.add_edge(node['uid'], link['switch'], key=link['device'], rate=link['rate'])
                        n_added_interfaces += 1
                        if n_added_interfaces == n_interfaces_to_consider:
                            break

        # all non-compute nodes have number of cores and memory size set to 0
        for u in g.nodes():
            if 'nb_cores' not in g.nodes[u] or 'ram_size' not in g.nodes[u]:
                g.nodes[u]['nb_cores'] = 0
                g.nodes[u]['ram_size'] = 0
        return cls(g)

    @classmethod
    def create_random_nw(cls, n_nodes):
        """ random network
        """
        raise NotImplementedError

    @classmethod
    def crete_test_nw(cls):
        """ small network to run tests
        """
        raise NotImplementedError

    @classmethod
    def read_from_file(cls, filename):
        """ from file
        """
        raise NotImplementedError
