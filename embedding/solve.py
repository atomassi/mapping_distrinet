"""
Base class
"""
import logging
import time
from abc import abstractmethod, ABCMeta


class Embed(object, metaclass=ABCMeta):

    def __init__(self, virtual, physical):
        self.virtual = virtual
        self.physical = physical
        self._log = logging.getLogger(__name__)

    @abstractmethod
    def __call__(self, **kwargs):
        """This method must be implemented"""
