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
