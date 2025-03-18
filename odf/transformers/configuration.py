from lark import Transformer, Tree

from odf.core.types import Configuration
from odf.transformers.mixins.mappings import BooleanMappingMixin


class ConfigurationTransformer(Transformer, BooleanMappingMixin):
    """Transforms a configuration parse tree into a dictionary mapping node names to boolean values."""
    def configuration(self, items):
        return self.mappings_to_dict(items)


def parse_configuration(configuration_tree: Tree) -> Configuration:
    assert configuration_tree.data == "configuration"
    transformer = ConfigurationTransformer()
    return transformer.transform(configuration_tree)
