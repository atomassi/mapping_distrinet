"""
Base exceptions and errors.
"""


class EmptySolutionError(Exception):
    """Exception for Empty Solution."""


class InfeasibleError(Exception):
    """Raised if a feasible solution has not been found."""


class TimeLimitError(Exception):
    """Raised if time limit has expired."""


class LinkCapacityError(Exception):
    """Raised if link capacity has been exceeded."""


class NodeResourceError(Exception):
    """Raised if node capacity has been exceeded."""


class AssignmentError(Exception):
    """Raised if some resource has not been assigned."""


class NoPathFoundError(Exception):
    """Raised a path has not been found."""


# solution status
NotSolved = 0
Solved = 1
Infeasible = -1

SolutionStatus = {NotSolved: "Not Solved", Solved: "Solved", Infeasible: "Infeasible"}

""" 
from enum import Enum

class SolutionStatus(Enum):
    infeasible = -1
    not_solved = 0
    solved = 1
    
    def __str__(self):
        return self.name
"""
