from lark import Transformer

from src.models.disruption_tree import DisruptionTree, DTNode


# noinspection PyMethodMayBeStatic,PyRedundantParentheses
class DisruptionTreeTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.tree = DisruptionTree()

    def probability(self, items):
        return ("probability", float(items[0].value))

    def objects(self, items):
        # items[0] is node_list result with list of names
        return ("objects", items[0])

    def node_list(self, items):
        # Each item is a NODE_NAME token
        return [item.value for item in items]

    def node_atom(self, items):
        return items[0].value

    def and_formula(self, items):
        return " && ".join(items)

    def or_formula(self, items):
        return " || ".join(items)

    def impl_formula(self, items):
        assert len(items) == 2
        return f"{items[0]} => {items[1]}"

    def equiv_formula(self, items):
        assert len(items) == 2
        return f"{items[0]} == {items[1]}"

    def nequiv_formula(self, items):
        assert len(items) == 2
        return f"{items[0]} != {items[1]}"

    def neg_formula(self, items):
        return f"!{items[0]}"

    def boolean_formula(self, items):
        # At this point, items will be a single string with the complete formula
        return items[0]

    def condition(self, items):
        return ("condition", items[0])

    def attribute_list(self, items):
        # Convert list of (key, value) tuples into a dict
        return dict(items)

    def basic_node(self, items):
        name = items[0].value
        attrs = {}
        if len(items) > 1:
            assert len(items) == 2
            attrs = items[1]  # Transformed attribute_list

        # Create node if it doesn't exist
        if not self.tree.has_node(name):
            node = DTNode(name, **attrs)
            self.tree.add_node(name, data=node)
        else:
            # Update existing node with attributes
            node = self.tree.nodes[name]["data"]
            node.update_from_attrs(attrs)

        return name

    def and_gate(self, _):
        return "AND"

    def or_gate(self, _):
        return "OR"

    def intermediate_node(self, items):
        parent = items[0].value
        gate_type = items[1]  # "AND" or "OR" from gate

        # Create parent node if it doesn't exist
        if not self.tree.has_node(parent):
            self.tree.add_node(parent, data=DTNode(parent, gate_type=gate_type))
        else:
            # Update existing node with gate type
            node = self.tree.nodes[parent]["data"]
            node.gate_type = gate_type

        # Both AND and OR gates add edges from parent to children
        if gate_type in ("AND", "OR"):
            # Create child nodes and edges
            children = [child.value for child in items[2:]]
            for child in children:
                # Create child node if it doesn't exist
                if not self.tree.has_node(child):
                    self.tree.add_node(child, data=DTNode(child))
                self.tree.add_edge(parent, child)

        return parent

    def tln(self, items):
        name = items[0].value
        if not self.tree.has_node(name):
            self.tree.add_node(name, data=DTNode(name))
        return name

    def disruption_tree(self, _):
        return self.tree
