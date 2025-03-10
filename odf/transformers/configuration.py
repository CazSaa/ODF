from lark import Transformer

from odf.transformers.mixins.mappings import BooleanMappingMixin


class ConfigurationTransformer(Transformer, BooleanMappingMixin):
    """Transforms a configuration parse tree into a dictionary mapping node names to boolean values."""
    def configuration(self, items):
        return self.mappings_to_dict(items)
