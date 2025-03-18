from dd import cudd
from lark import Transformer, Visitor, Tree
from lark.visitors import _Leaf_T

from odf.models.disruption_tree import DisruptionTree, DTNode
from odf.models.object_graph import ObjectGraph
from odf.transformers.mixins.boolean_formula import BooleanFormulaMixin
from odf.transformers.mixins.mappings import BooleanMappingMixin


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


class ConditionTransformer(Transformer, BooleanFormulaMixin):
    def __init__(self, bdd: cudd.BDD):
        super().__init__()
        self.bdd = bdd


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
class Layer1BDDTransformer(Transformer, BooleanMappingMixin,
                           BooleanFormulaMixin):
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
        self.bdd_vars: list[str] = []
        self.bdd = cudd.BDD()
        self.prime_count = 0

    def transform(self, tree: Tree[_Leaf_T]) -> cudd.Function:
        visitor = Layer1FormulaVisitor(self.attack_tree, self.fault_tree,
                                       self.object_graph)
        visitor.visit(tree)

        self.attack_nodes = visitor.attack_nodes
        self.fault_nodes = visitor.fault_nodes
        self.object_properties = visitor.object_properties

        self.bdd_vars = [*visitor.object_properties, *visitor.fault_nodes,
                         *visitor.attack_nodes]
        self.bdd.declare(*self.bdd_vars)
        return super().transform(tree)

    def with_boolean_evidence(self, items):
        # TODO caz discuss how to handle OPs, and intermediate nodes. Also
        #  consider raising error if illegal thing has evidence set because
        #  currently cudd.pyx will throw a cryptic ValueError
        formula, evidence_dict = items
        return self.bdd.let(evidence_dict, formula)

    def boolean_evidence(self, items):
        return self.mappings_to_dict(items)

    def mrs(self, items):
        self.prime_count += 1

        def p(var):
            return f"{var}'{self.prime_count}"

        formula = items[0]
        vars_ = formula.support - self.object_properties
        primed_vars = [p(var) for var in vars_]
        self.bdd.declare(*primed_vars)

        primed_formula = self.bdd.let({var: p(var) for var in vars_},
                                      formula)

        # Construct the primes_subset formula:
        # 1. First part: conjunction of implications (p'i => xi)
        implications = self.bdd.true
        for var in vars_:
            prime_var = self.bdd.var(p(var))
            orig_var = self.bdd.var(var)
            implication = prime_var.implies(orig_var)
            implications = implications & implication

        # 2. Second part: disjunction of XORs ((p'i ^ xi) | (p'j ^ xj) | ...)
        xor_terms = self.bdd.false
        for var in vars_:
            prime_var = self.bdd.var(p(var))
            orig_var = self.bdd.var(var)
            xor_term = self.bdd.apply('xor', prime_var, orig_var)
            xor_terms = xor_terms | xor_term

        # Combine both parts
        primes_subset = implications & xor_terms

        return formula & ~self.bdd.exist(primed_vars,
                                         primes_subset & primed_formula)

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
