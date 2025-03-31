from fractions import Fraction

from odf.core.exceptions import ODFError


class MissingNodeProbabilityError(ODFError):
    """Raised when a node is missing required probability information."""

    def __init__(self, node_name: str, tree_type: str):
        self.node_name = node_name
        self.tree_type = tree_type
        super().__init__(
            f"Node '{node_name}' in the {tree_type} has no probability")


class ConfigurationError(ODFError):
    """Base class for configuration-related errors."""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration variables are missing."""

    def __init__(self, missing_vars: set[str], type_name: str = "variables"):
        self.missing_vars = missing_vars
        self.type_name = type_name
        super().__init__(
            f"Missing {type_name} in configuration: {missing_vars}")


class UnknownNodeError(ODFError):
    """Raised when referencing a node that doesn't exist."""

    def __init__(self, node_name: str):
        self.node_name = node_name
        super().__init__(f"You referenced an unknown node: {node_name}")


class EvidenceError(ODFError):
    """Base class for evidence-related errors."""
    pass


class NodeAncestorEvidenceError(EvidenceError):
    """Raised when evidence is set for a node that is a descendant of another node with evidence."""

    def __init__(self, node_name: str, ancestor_name: str):
        self.node_name = node_name
        super().__init__(
            f"You cannot reference node '{node_name}' because evidence is set for its ancestor '{ancestor_name}'")


class EvidenceAncestorEvidenceError(EvidenceError):
    """Raised when evidence is set for a node that is a descendant of another node with evidence."""

    def __init__(self, node_name: str, ancestor_name: str):
        self.node_name = node_name
        super().__init__(
            f"You cannot set evidence for node '{node_name}' because evidence is already set for its ancestor '{ancestor_name}'")


class InvalidNodeEvidenceError(EvidenceError):
    """Raised when trying to set evidence for an invalid node."""

    def __init__(self, node_name: str):
        self.node_name = node_name
        super().__init__(
            f"You cannot set evidence for non-existent node: {node_name}")


class NonModuleNodeError(ODFError):
    """Raised when a node is expected to be a module but isn't."""

    def __init__(self, node_name: str, tree_type: str):
        self.node_name = node_name
        self.tree_type = tree_type
        super().__init__(
            f"Node '{node_name}' in {tree_type} is not a module. Evidence can only be set for modules.")


class InvalidProbabilityError(ODFError):
    """Raised when a probability value is invalid."""

    def __init__(self, node_name: str, value: Fraction):
        self.value = value
        super().__init__(
            f"Probability for node '{node_name}' must be between 0 and 1 (got {value:f})")


class InvalidImpactError(ODFError):
    """Raised when an impact value is invalid."""

    def __init__(self, node_name: str, value: Fraction):
        self.value = value
        super().__init__(
            f"Impact for node '{node_name}' must be non-negative (got {value:f})")
