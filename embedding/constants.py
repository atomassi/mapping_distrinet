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


# solution status
NotSolved = 0
Solved = 1
Infeasible = -1

EmbedStatus = {NotSolved: "Not Solved",
          Solved: "Solved",
          Infeasible: "Infeasible"
          }
