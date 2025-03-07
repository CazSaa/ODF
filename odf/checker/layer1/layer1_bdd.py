from dd import cudd
from lark import Transformer, Visitor, Tree
from lark.visitors import _Leaf_T, _Return_T

from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph


class Layer1FormulaVisitor(Visitor):
    def __init__(self,
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_graph: ObjectGraph):
        super().__init__()
        self.attack_tree = attack_tree
        self.fault_tree = fault_tree
        self.object_graph = object_graph
        self.attack_nodes, self.fault_nodes, self.object_properties = set(), set(), set()

    def node_atom(self, node_atom):
        node_name = node_atom.children[0].value

        for disruption_tree, collection in [
            (self.attack_tree, self.attack_nodes),
            (self.fault_tree, self.fault_nodes)]:
            if disruption_tree.has_node(node_name):
                collection.update(disruption_tree.get_basic_descendants(node_name))

                for descendant in disruption_tree.get_descendants(node_name):
                    self.object_properties.update(
                        disruption_tree.nodes[descendant]["data"].object_properties)
                return

        if self.object_graph.has_object_property(node_name):
            self.object_properties.add(node_name)
            return

        raise ValueError(f"Unknown node: {node_name}")


class Layer1BDDTransformer(Transformer):
    """Transforms a layer 1 formula parse tree into a BDD."""

    def __init__(self,
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_graph: ObjectGraph):
        super().__init__()
        self.attack_tree = attack_tree
        self.fault_tree = fault_tree
        self.object_graph = object_graph
        self.bdd = cudd.BDD()

    def transform(self, tree: Tree[_Leaf_T]) -> _Return_T:
        visitor = Layer1FormulaVisitor(self.attack_tree, self.fault_tree,
                                       self.object_graph)
        visitor.visit(tree)

        self.bdd.declare(*visitor.object_properties, *visitor.fault_nodes,
                         *visitor.attack_nodes)
        super().transform(tree)
