from lark import Transformer


# noinspection PyMethodMayBeStatic
class ConfigurationTransformer(Transformer):
    """Transforms a configuration parse tree into a dictionary mapping node names to boolean values."""

    def boolean_mapping(self, items):
        """Transform a boolean mapping (e.g., 'A:1') into a tuple (name, bool)."""
        name = items[0].value
        truth_value = items[1].value == "1"
        return name, truth_value

    def configuration(self, items):
        """Transform a configuration tree into a dictionary of boolean values."""
        if not items:  # If no boolean mappings
            return {}        
        return dict(items)

    def boolean_evidence(self, items):
        """Transform a list of boolean mappings into a list of (name, bool) tuples."""
        return items