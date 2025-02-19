from odf.core.exceptions import ODFError


class CrossReferenceError(ODFError):
    """Raised when cross-reference validation between different trees fails."""
    pass
