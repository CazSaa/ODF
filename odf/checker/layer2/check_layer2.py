from fractions import Fraction

from dd import cudd
from lark import Transformer, Tree

from odf.checker.layer1.layer1_bdd import Layer1BDDTransformer
from odf.core.types import Configuration
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph
from odf.transformers.configuration import parse_configuration
from odf.transformers.mixins.boolean_eval import BooleanEvalMixin


def l2_prob(attack_tree: DisruptionTree,
            fault_tree: DisruptionTree,
            bdd: cudd.Function,
            configuration: Configuration) -> float:
    root = bdd
    while root.var in configuration:
        if configuration[root.var]:
            root = root.high
        else:
            root = root.low

    return calc_node_prob(attack_tree, fault_tree, root)


def calc_node_prob(attack_tree: DisruptionTree,
                   fault_tree: DisruptionTree,
                   root: cudd.Function) -> float:
    manager = root.bdd
    probs = {manager.true: Fraction(1), manager.false: (Fraction(0))}
    for node in manager.node_iter(root):
        if node in probs:
            continue

        if node.var in fault_tree:
            node_prob = fault_tree.nodes[node.var]["data"].probability
            if node_prob is None:
                # todo caz
                raise ValueError(
                    f"Node {node.var} has no probability in the fault tree")
            p_low = probs[node.low] * (Fraction(1) - node_prob)
            p_high = probs[node.high] * node_prob
            probs[node] = p_low + p_high
        elif node.var in attack_tree:
            node_prob = attack_tree.nodes[node.var]["data"].probability
            if node_prob is None:
                # todo caz
                raise ValueError(
                    f"Node {node.var} has no probability in the attack tree")
            p_low = probs[node.low]
            p_high = probs[node.high] * node_prob
            probs[node] = max(p_low, p_high)
        else:
            raise AssertionError(
                "We should only encounter nodes from the attack or fault tree")
    return probs[root]


# todo caz prob evidence

# noinspection PyMethodMayBeStatic
class Layer2Transformer(Transformer, BooleanEvalMixin):
    def __init__(self,
                 configuration: Configuration,
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_graph: ObjectGraph):
        super().__init__()
        self.configuration = configuration
        self.attack_tree = attack_tree
        self.fault_tree = fault_tree
        self.object_graph = object_graph
        self.used_object_properties = set()

    def probability_formula(self, items):
        formula_tree, relation, threshold = items

        l1_transformer = Layer1BDDTransformer(
            self.attack_tree, self.fault_tree, self.object_graph,
            reordering=False)
        bdd = l1_transformer.transform(formula_tree)

        needed_vars = l1_transformer.object_properties.intersection(bdd.support)
        given_vars = set(self.configuration.keys())
        missing_vars = needed_vars - given_vars
        if len(missing_vars) > 0:
            # todo caz
            raise ValueError(
                f"Missing object properties in configuration: {missing_vars}")
        self.used_object_properties.update(needed_vars)

        prob = l2_prob(self.attack_tree, self.fault_tree, bdd,
                       self.configuration)

        print(f"INFO: Probability: {prob}")  # todo caz reconstruct the formula

        match relation:
            case "<":
                return prob < threshold
            case "<=":
                return prob <= threshold
            case "==":
                return prob == threshold
            case ">=":
                return prob >= threshold
            case ">":
                return prob > threshold
            case _:
                raise ValueError("Invalid relation")

    def DECIMAL(self, items):
        return Fraction(items.value)


def check_layer2_query(formula: Tree,
                       attack_tree: DisruptionTree,
                       fault_tree: DisruptionTree,
                       object_graph: ObjectGraph):
    assert formula.data == "layer2_query"
    assert formula.children[0].data == "configuration"
    configuration = parse_configuration(formula.children[0])
    non_object_properties = set(configuration.keys()) - set(
        object_graph.object_properties)
    if len(non_object_properties) > 0:
        # todo caz
        print(
            f"WARNING: The following variables of the configuration are not"
            f" object properties and will be ignored: {non_object_properties}")
        for var in non_object_properties:
            del configuration[var]

    transformer = Layer2Transformer(configuration, attack_tree, fault_tree,
                                    object_graph)
    res = transformer.transform(formula.children[1])

    surplus_vars = set(
        configuration.keys()) - transformer.used_object_properties
    if len(surplus_vars) > 0:
        # todo caz
        print(
            f"WARNING: You provided object properties in the configuration that"
            f" are not used in the formula, these can be removed: {surplus_vars}")

    return res
