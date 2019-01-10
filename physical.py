import json
import logging

import networkx as nx

from definitions import *


class PhysicalNetwork(object):

    def __init__(self, g):
        self.g = g
        self._log = logging.getLogger(__name__)

    @classmethod
    def grid5000(cls, name):

        g = nx.MultiGraph()

        if name == "grisou":
            # switches, cannot be used to place tasks
            g.add_node("sgrisou1", nb_cores=0, ram_size=0)
            g.add_node("gw-nancy", nb_cores=0, ram_size=0)
            # this link is not is the json file - to be added manually
            g.add_edge("sgrisou1", "gw-nancy", key='switches_link', rate=10000000000)

        # compute node
        with open(os.path.join(basedir, "instances", "physical", name + ".json")) as f:
            data = json.load(f)

            for node in data['items']:
                g.add_node(node['uid'], nb_cores=node['architecture']['nb_cores'],
                           ram_size=node['main_memory']['ram_size'])

                for interface, link in enumerate(node['network_adapters']):
                    if link['enabled'] and link['interface'] == "Ethernet" and 'rate' in link:
                        g.add_edge(node['uid'], link['switch'], key=link['device'], rate=link['rate'])

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
