from typing import Literal


class MalformedTreeError(Exception):
    pass


class DuplicateObjectDefinitionError(MalformedTreeError):
    """Raised when an object is defined multiple times in the same context."""

    def __init__(self, object_name, type: Literal["basic", "intermediate"]):
        self.object_name = object_name
        self.type = type
        super().__init__(
            f"{type.capitalize()} object '{object_name}' is already defined")


class DuplicateNodeDefinitionError(MalformedTreeError):
    """Raised when a node is defined multiple times in the same context."""

    def __init__(self, node_name, type: Literal["basic", "intermediate"]):
        self.node_name = node_name
        self.type = type
        super().__init__(
            f"{type.capitalize()} node '{node_name}' is already defined")


class NotAcyclicError(MalformedTreeError):
    """Raised when a graph is not acyclic."""

    def __init__(self):
        super().__init__("Graph is not acyclic")


class NotConnectedError(MalformedTreeError):
    """Raised when a graph is not connected."""

    def __init__(self):
        super().__init__("Graph is not connected")


class NotExactlyOneRootError(MalformedTreeError):
    """Raised when a graph has more than one root."""

    def __init__(self):
        super().__init__("Graph has more than one root")
