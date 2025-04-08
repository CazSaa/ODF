"""
Utility functions for formatting CLI output.
"""
from odf.core.constants import COLOR_GREEN, COLOR_RED, COLOR_MAGENTA, \
    COLOR_CYAN, COLOR_RESET


def format_boolean(value: bool) -> str:
    """Format a boolean value with appropriate color."""
    color = COLOR_GREEN if value else COLOR_RED
    return f"{color}{value}{COLOR_RESET}"


def format_set(value: frozenset[str] | None) -> str:
    """Format each element in a set with cyan color."""
    if value is None:
        return "None"
    colored_items = [format_node_name(item) for item in sorted(value)]
    return "{" + ", ".join(colored_items) + "}"


def format_config(config: dict[str, bool]) -> str:
    """Format a configuration with cyan keys and colored boolean values."""
    items = [f"{format_node_name(key)}: {format_boolean(value)}"
             for key, value in config.items()]
    return "{" + ", ".join(items) + "}"


def format_node_name(name: str) -> str:
    """Format a node name with cyan color."""
    return f"{COLOR_CYAN}{name}{COLOR_RESET}"


def format_risk(risk: float) -> str:
    """Format a risk value with magenta color."""
    return f"{COLOR_MAGENTA}{risk}{COLOR_RESET}"
