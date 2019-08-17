import logging
from logging import NullHandler

from .constants import SolutionStatus
from .virtual import VirtualNetwork

logging.getLogger(__name__).addHandler(NullHandler())
