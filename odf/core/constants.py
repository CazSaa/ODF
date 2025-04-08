"""
Core constants for the ODF project.
"""
import shutil


def _get_terminal_width() -> int:
    """Get the terminal width or fall back to 80 columns."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


SEPARATOR_LENGTH = _get_terminal_width()

# ANSI Color Codes
COLOR_GRAY = "\033[90m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[33m"
COLOR_BLUE = "\033[34m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[36m"
COLOR_RED = "\033[91m"
COLOR_RESET = "\033[0m"
