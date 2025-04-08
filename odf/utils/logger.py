import logging

from odf.core.constants import COLOR_BLUE, COLOR_YELLOW, COLOR_RED, COLOR_GRAY, \
    COLOR_RESET


class ColorFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages."""

    COLORS = {
        'INFO': COLOR_BLUE,
        'WARNING': COLOR_YELLOW,
        'ERROR': COLOR_RED,
        'RESET': COLOR_RESET
    }
    indent = "    "

    def format(self, record):
        """Add color to the levelname and indent the message"""
        orig_levelname = record.levelname
        # Store the original message
        orig_message = record.msg
        # Color the levelname and indent
        record.levelname = (
            f"{self.indent}{self.COLORS.get(record.levelname, '')}"
            f"{record.levelname}{self.COLORS['RESET']}")
        # Color the message gray
        record.msg = f"{COLOR_GRAY}{orig_message}{COLOR_RESET}"
        # Format with both colored parts
        result = super().format(record)
        # Restore original values
        record.levelname = orig_levelname
        record.msg = orig_message
        return result


logger = logging.getLogger("odf")

# Set up console handler with custom formatter
console_handler = logging.StreamHandler()
formatter = ColorFormatter('%(levelname)s: %(message)s')
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.setLevel(logging.INFO)
