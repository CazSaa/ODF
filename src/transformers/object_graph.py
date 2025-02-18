from lark import Transformer

from src.models.object_graph import ObjectGraph, ObjectNode
from src.transformers.exceptions import DuplicateObjectDefinitionError


# noinspection PyMethodMayBeStatic
class ObjectGraphTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.graph = ObjectGraph()
        # Track which nodes have been defined as basic objects
        self.basic_objects = set()
        # Track which nodes have been defined as intermediate objects
        self.intermediate_objects = set()

    # noinspection PyRedundantParentheses
    def properties(self, items):
        return ("properties", items[0])

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

    def tln(self, items):
        name = items[0].value
        if not self.graph.has_node(name):
            self.graph.add_node(name, data=ObjectNode(name))
        return name

    def object_graph_tree(self, _):
        return self.graph
