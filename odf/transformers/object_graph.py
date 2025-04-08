from collections import defaultdict

from lark import Transformer

from odf.models.object_graph import ObjectGraph, ObjectNode
from odf.transformers.exceptions import DuplicateObjectDefinitionError, \
    DuplicateObjectPropertyError


# noinspection PyMethodMayBeStatic
class ObjectGraphTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.graph = ObjectGraph()
        # Track which nodes have been defined as basic objects
        self.basic_objects = set()
        # Track which nodes have been defined as intermediate objects
        self.intermediate_objects = set()
        # Track which objects use each property
        self.property_objects: dict[str, set[str]] = defaultdict(set)

    # noinspection PyRedundantParentheses
    def properties(self, items):
        properties = items[0] if items else []
        return ("properties", properties)

    def node_list(self, items):
        # Each item is a NODE_NAME token
        return [item.value for item in items]

    def basic_object(self, items):
        name = items[0].value
        if name in self.basic_objects:
            raise DuplicateObjectDefinitionError(name, "basic")

        attrs = {}
        if len(items) > 1:
            assert len(items) == 2
            # Transformed properties list (key being "properties")
            attrs = dict([items[1]])

            # Track which properties are used by this object
            if "properties" in attrs:
                properties = attrs["properties"]
                for prop in properties:
                    # Check if property is already used by another object
                    if self.property_objects[prop] and name not in \
                            self.property_objects[prop]:
                        raise DuplicateObjectPropertyError(prop, (
                                    self.property_objects[prop] | {name}))
                    self.property_objects[prop].add(name)

        # Create node if it doesn't exist (might exist from intermediate object)
        if not self.graph.has_node(name):
            node = ObjectNode(name, **attrs)
            self.graph.add_node(name, data=node)
        else:
            # Update existing node with properties
            node = self.graph.nodes[name]["data"]
            node.update_from_attrs(attrs)

        self.basic_objects.add(name)
        return name

    def intermediate_object(self, items):
        parent = items[0].value
        if parent in self.intermediate_objects:
            raise DuplicateObjectDefinitionError(parent, "intermediate")

        # Create parent node if it doesn't exist
        if not self.graph.has_node(parent):
            self.graph.add_node(parent, data=ObjectNode(parent))

        # Create child nodes and edges ("has" relationships)
        children = [child.value for child in items[1:]]
        for child in children:
            # Create child node if it doesn't exist
            if not self.graph.has_node(child):
                self.graph.add_node(child, data=ObjectNode(child))
            self.graph.add_edge(parent, child)

        self.intermediate_objects.add(parent)
        return parent

    def object_graph_tree(self, _):
        self.graph.validate_tree()
        return self.graph

    def object_graph(self, items):
        return items[0]
