# noinspection PyMethodMayBeStatic
class BooleanMappingMixin:
    def boolean_mapping(self, items):
        """Transform a boolean mapping (e.g., 'A:1') into a tuple (name, bool)."""
        name = items[0].value
        truth_value = items[1].value == "1"
        return name, truth_value

    def mappings_to_dict(self, items):
        """Transform a configuration tree into a dictionary of boolean values."""
        if not items:  # If no boolean mappings
            return {}
        return dict(items)
