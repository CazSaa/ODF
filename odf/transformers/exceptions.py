from typing import Literal

from lark.exceptions import VisitError

from odf.core.exceptions import ODFError


class MyVisitError(ODFError):
    """Wrapper for Lark.VisitError that includes the specific tree that caused
    the error."""

    def __init__(self, visit_error: VisitError, part: str):
        self.visit_error = visit_error
        self.part = part
        super().__init__(f"Visit error: {visit_error}")


class MalformedTreeError(ODFError):
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


class DuplicateObjectPropertyError(MalformedTreeError):
    """Raised when the same property name is used on multiple objects."""

    def __init__(self, property_name: str, objects: set[str]):
        self.property_name = property_name
        self.objects = objects
        super().__init__(
            f"Property '{property_name}' is used by multiple objects: {objects}")
