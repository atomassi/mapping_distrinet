import json
import logging
import os
import warnings

_log = logging.getLogger(__name__)


class CloudInstance(object):
    def __init__(self, vm_options):
        self._vm_options = vm_options

    @property
    def vm_options(self):
        return self._vm_options

    @vm_options.setter
    def vm_options(self, new_vm_options):
        warnings.warn("original VMs instances have been modified")
        self._vm_options = new_vm_options

    def memory(self, vm):
        return self._vm_options[vm]["memory"]

    def cores(self, vm):
        return self._vm_options[vm]["vCPU"]

    def hourly_cost(self, vm):
        return self._vm_options[vm]["hourly_cost"]

    @classmethod
    def read_ec2_instances(cls, vm_type="general_purpose"):
        with open(os.path.join(vm_type + ".json",)) as f:
            vm_options = json.load(f)
        # gibibyte to mebibyte conversion
        for vm in vm_options:
            vm_options[vm]["memory"] *= 1024

        return cls(vm_options)
