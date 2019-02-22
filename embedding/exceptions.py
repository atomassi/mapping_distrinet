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

    def __init__(self, link, used=None, maximum=None):
        if used and maximum:
            message = f"capacity exeeded on Physical Link {link}, used {used} capacity {maximum}"
        else:
            message = f"capacity exeeded on Physical Link {link}"
        super().__init__(message)


class NodeResourceError(Exception):
    """Raised if node capacity has been exceeded."""

    def __init__(self, node, resource_type, used=None, maximum=None):
        if used and maximum:
            message = f"{resource_type} exeeded on Physical Node {node}, used {used} capacity {maximum}"
        else:
            message = f"{resource_type} exeeded on Physical Node {node}"
        super().__init__(message)


class AssignmentError(Exception):
    """Raised if some resource has not been assigned."""

    def __init__(self, resource):
        message = f"{resource} not assigned"
        super().__init__(message)
