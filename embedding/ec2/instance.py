import json
import os
import warnings


class InstanceEC2(object):
    def __init__(self, instances):
        self._instances = instances

    @property
    def instances(self):
        return self._instances

    @instances.setter
    def instances(self, instances_new):
        warnings.warn("original VMs instances have been modified")
        self._instances = instances_new

    def get_memory(self, vm):
        return self._instances[vm]['memory']

    def get_cores(self, vm):
        return self._instances[vm]['vCPU']

    def get_hourly_cost(self, vm):
        return self._instances[vm]['hourly_cost']

    @classmethod
    def get_EC2_vritual_machines(cls, vm_type='general_purpose'):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "instances", vm_type + ".json")) as f:
            instances = json.load(f)
        # gibibyte to mebibyte conversion
        for instance_name in instances:
            instances[instance_name]['memory'] *= 1024

        return cls(instances)
