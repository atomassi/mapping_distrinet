"""
Utility class used to implement Bins
"""

class Bin(object):
    """ Container for virtual nodes mapped on the Bin associated to a VM """

    def __init__(self, vm_type):
        self.vm_type = vm_type
        self.items = set()
        self.used_cores = 0
        self.used_memory = 0

    def add_item(self, u, req_cores, req_memory):
        self.items.add(u)
        self.used_cores += req_cores
        self.used_memory += req_memory

    def __str__(self):
        """ Printable representation """
        return f"Bin(vm_type={self.vm_type}, items={self.items}, used cores={self.used_cores}, used memory={self.used_memory})"
