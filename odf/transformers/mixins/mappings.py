from fractions import Fraction

from odf.transformers.mixins.decorators import interpreter_or_transformer


# noinspection PyMethodMayBeStatic
class BooleanMappingMixin:
    @interpreter_or_transformer
    def boolean_mapping(self, items):
        """Transform a boolean mapping (e.g., 'A:1') into a tuple (name, bool)."""
        name = items[0].value
        truth_value = items[1].value == "1"
        return name, truth_value

    @interpreter_or_transformer
    def probability_mapping(self, items):
        # Guaranteed by the grammar: children[0] is NODE_NAME and children[1] is PROB_VALUE.
        return items[0].value, Fraction(items[1].value)

    @staticmethod
    def mappings_to_dict(items):
        """Transform a configuration tree into a dictionary of boolean values."""
        if not items:  # If no boolean mappings
            return {}
        return dict(items)
