from dd import cudd
from lark import Transformer, Visitor, Tree
from lark.visitors import _Leaf_T, _Return_T

from odf.models.disruption_tree import DisruptionTree, DTNode
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
                collection.update(
                    disruption_tree.get_basic_descendants(node_name))

                for descendant in disruption_tree.get_descendants(node_name):
                    self.object_properties.update(
                        disruption_tree.nodes[descendant][
                            "data"].object_properties)
                return

        if self.object_graph.has_object_property(node_name):
            self.object_properties.add(node_name)
            return

        raise ValueError(f"Unknown node: {node_name}")


# noinspection PyMethodMayBeStatic
class ConditionTransformer(Transformer):
    def __init__(self, bdd: cudd.BDD):
        super().__init__()
        self.bdd = bdd

    def impl_formula(self, items):
        formula1, formula2 = items
        return formula1.implies(formula2)

    def or_formula(self, items):
        return items[0] | items[1]

    def and_formula(self, items):
        return items[0] & items[1]

    def equiv_formula(self, items):
        formula1, formula2 = items
        return self.bdd.apply('equiv', formula1, formula2)

    def nequiv_formula(self, items):
        formula1, formula2 = items
        return self.bdd.apply('xor', formula1, formula2)

    def node_atom(self, items):
        return self.bdd.var(items[0].value)

    def neg_formula(self, items):
        return ~items[0]


def basic_node_to_bdd(bdd: cudd.BDD, node: DTNode):
    if node.condition_tree is None:
        return bdd.var(node.name)
    condition_bdd = ConditionTransformer(bdd).transform(node.condition_tree)
    return bdd.var(node.name) & condition_bdd


def intermediate_node_to_bdd(bdd: cudd.BDD, disruption_tree: DisruptionTree,
                             node_name: str) -> cudd.Function:
    node = disruption_tree.nodes[node_name]["data"]
    if disruption_tree.out_degree(node_name) == 0:
        return basic_node_to_bdd(bdd, node)

    children = list(disruption_tree.successors(node_name))

    if len(children) == 1:
        return intermediate_node_to_bdd(bdd, disruption_tree, children[0])

    assert node.gate_type is not None
    apply = node.gate_type

    result = intermediate_node_to_bdd(bdd, disruption_tree, children[0])
    for child in children[1:]:
        result = bdd.apply(apply, result,
                           intermediate_node_to_bdd(bdd, disruption_tree,
                                                    child))

    if node.condition_tree is None:
        return result
    condition_bdd = ConditionTransformer(bdd).transform(node.condition_tree)
    return result & condition_bdd


# noinspection PyMethodMayBeStatic
class Layer1BDDTransformer(Transformer):
    """Transforms a layer 1 formula parse tree into a BDD."""

    attack_nodes: set[str]
    fault_nodes: set[str]
    object_properties: set[str]

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

        self.attack_nodes = visitor.attack_nodes
        self.fault_nodes = visitor.fault_nodes
        self.object_properties = visitor.object_properties

        self.bdd.declare(*visitor.object_properties, *visitor.fault_nodes,
                         *visitor.attack_nodes)
        return super().transform(tree)

    def with_boolean_evidence(self, items):
        raise NotImplementedError()

    def impl_formula(self, items):
        formula1, formula2 = items
        return formula1.implies(formula2)

    def or_formula(self, items):
        return items[0] | items[1]

    def and_formula(self, items):
        return items[0] & items[1]

    def equiv_formula(self, items):
        formula1, formula2 = items
        return self.bdd.apply('equiv', formula1, formula2)

    def nequiv_formula(self, items):
        formula1, formula2 = items
        return self.bdd.apply('xor', formula1, formula2)

    def mrs(self, items):
        formula = items[0]
        raise NotImplementedError()

    def node_atom(self, items):
        node_name = items[0].value

        if node_name in self.bdd.vars:
            if node_name in self.object_properties:
                return self.bdd.var(node_name)

            if node_name in self.attack_nodes:
                node = self.attack_tree.nodes[node_name]["data"]
                return basic_node_to_bdd(self.bdd, node)
            if node_name in self.fault_nodes:
                node = self.fault_tree.nodes[node_name]["data"]
                return basic_node_to_bdd(self.bdd, node)

            raise ValueError(f"Unknown node: {node_name}")

        for disruption_tree in [self.attack_tree, self.fault_tree]:
            if disruption_tree.has_intermediate_node(node_name):
                return intermediate_node_to_bdd(self.bdd, disruption_tree,
                                                node_name)

        if node_name not in self.bdd.vars:
            raise ValueError(f"Unknown node: {node_name}")

    def neg_formula(self, items):
        return ~items[0]
