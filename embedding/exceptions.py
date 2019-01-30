class EmptySolutionError(Exception):
    def __init__(self):
        super().__init__("empty solution")


class LinkCapacityError(Exception):
    def __init__(self, link, used=None, maximum=None):
        if used and maximum:
            message = f"capacity exeeded on Physical Link {link}, used {used} capacity {maximum}"
        else:
            message = f"capacity exeeded on Physical Link {link}"
        super().__init__(message)


class NodeResourceError(Exception):
    def __init__(self, node, resource_type, used=None, maximum=None):
        if used and maximum:
            message = f"{resource_type} exeeded on Physical Node {node}, used {used} capacity {maximum}"
        else:
            message = f"{resource_type} exeeded on Physical Node {node}"
        super().__init__(message)


class AssignmentError(Exception):
    def __init__(self, resource):
        message = f"{resource} not assigned"
        super().__init__(message)


class InfeasibleError(Exception):
    def __init__(self):
        super().__init__("Input Instance cannot be mapped")


class TimeLimitError(Exception):
    def __init__(self):
        super().__init__("Time limit expired and no feasible solution has been found")
