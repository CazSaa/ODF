import logging


class ColorFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages."""

    COLORS = {
        'INFO': '\033[94m',  # Blue
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',  # Red
        'RESET': '\033[0m'  # Reset color
    }

    def format(self, record):
        orig_levelname = record.levelname

        # Add color to the levelname
        record.levelname = f"{self.COLORS.get(record.levelname, '')}{record.levelname}{self.COLORS['RESET']}"
        # Format the message
        result = super().format(record)
        # Restore the original levelname
        record.levelname = orig_levelname

        return result


logger = logging.getLogger("odf")

# Set up console handler with custom formatter
console_handler = logging.StreamHandler()
formatter = ColorFormatter('%(levelname)s: %(message)s')
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.setLevel(logging.INFO)
