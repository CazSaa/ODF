from collections import deque
from fractions import Fraction
from typing import Iterator

from dd import cudd
from dd.cudd import Function
from lark import Tree
from lark.visitors import Interpreter, visit_children_decor

from odf.checker.exceptions import MissingNodeProbabilityError, \
    MissingConfigurationError
from odf.checker.layer1.layer1_bdd import Layer1BDDInterpreter
from odf.core.types import Configuration
from odf.models.disruption_tree import DisruptionTree
from odf.models.object_graph import ObjectGraph
from odf.transformers.configuration import parse_configuration
from odf.transformers.prob_evidence_prepass import PrePassEvidenceInterpreter


def dfs_nodes_with_complement(
        root: cudd.Function, is_complement: bool
) -> Iterator[tuple[Function, bool]]:
    """
    Generator that traverses the BDD in reverse-topological order in a
    non-recursive manner. For each node it yields a tuple: (node, complemented)
    where 'complemented' is True if an odd number of complemented edges were taken
    on the path from the original root to 'node'.

    Note:
      - Each node supports a "negated" attribute (True if the pointer is complemented).
      - Each node supports a "regular" property that returns the underlying (uncomplemented) node.
    """
    # Each stack element is a tuple: (node, complement_flag, visited_flag)
    stack = deque([(root, is_complement, False)])
    yielded = set()  # To avoid yielding the same (node, complement) pair more than once.
    iters = 0
    max_len = 0

    while stack:
        iters += 1
        max_len = max(max_len, len(stack))
        node, comp, visited = stack.pop()
        if (node, comp) in yielded:
            continue
        if visited:
            yielded.add((node, comp))
            yield node, comp
            continue

        # Mark the current node as visited
        stack.append((node, comp, True))

        # Terminal node?
        if node.var is None:
            continue

        # Process children (both low and high children)
        for child in (node.low, node.high):
            new_comp = comp ^ child.negated  # toggle complement flag if edge is complemented

            child_regular = child.regular
            stack.append((child_regular, new_comp, False))


def l2_prob(attack_tree: DisruptionTree,
            fault_tree: DisruptionTree,
            bdd: cudd.Function,
            configuration: Configuration,
            prob_evidence: dict) -> Fraction:
    root = bdd
    complemented = root.negated
    while root.var in configuration:
        if configuration[root.var]:
            root = root.high
        else:
            root = root.low
            complemented ^= root.negated

    return calc_node_prob(attack_tree, fault_tree, root, complemented,
                          prob_evidence)


def calc_node_prob(attack_tree: DisruptionTree,
                   fault_tree: DisruptionTree,
                   root: cudd.Function,
                   is_complement: bool,
                   prob_evidence: dict) -> Fraction:
    manager = root.bdd

    probs = {
        manager.true: Fraction(1),
        manager.false: Fraction(0),
    }

    def to_key(node_: Function, complemented_: bool) -> Function:
        return node_ if not complemented_ else manager.apply("not", node_)

    for node, complemented in dfs_nodes_with_complement(root.regular,
                                                        is_complement):
        if to_key(node, complemented) in probs:
            continue

        # If we have evidence for this node, use it instead of the node's probability
        if node.var in fault_tree:
            if node.var in prob_evidence:
                node_prob = prob_evidence[node.var]
            else:
                node_prob = fault_tree.nodes[node.var]["data"].probability
                if node_prob is None:
                    raise MissingNodeProbabilityError(node.var, "fault tree")
            p_low = probs[to_key(node.low, complemented)] * (
                    Fraction(1) - node_prob)
            p_high = probs[to_key(node.high, complemented)] * node_prob
            probs[to_key(node, complemented)] = p_low + p_high
        elif node.var in attack_tree:
            if node.var in prob_evidence:
                node_prob = prob_evidence[node.var]
            else:
                node_prob = attack_tree.nodes[node.var]["data"].probability
                if node_prob is None:
                    raise MissingNodeProbabilityError(node.var, "attack tree")
            p_low = probs[to_key(node.low, complemented)]
            p_high = probs[to_key(node.high, complemented)] * node_prob
            probs[to_key(node, complemented)] = max(p_low, p_high)
        else:
            raise AssertionError(
                "We should only encounter nodes from the attack or fault tree")
    return probs[to_key(root.regular, is_complement)]


# noinspection PyMethodMayBeStatic
class Layer2Interpreter(Interpreter):
    def __init__(self,
                 configuration: Configuration,
                 attack_tree: DisruptionTree,
                 fault_tree: DisruptionTree,
                 object_graph: ObjectGraph,
                 prob_evidence: dict[int, Fraction]):
        super().__init__()
        self.configuration = configuration
        self.attack_tree = attack_tree
        self.fault_tree = fault_tree
        self.object_graph = object_graph
        self.used_object_properties = set()
        # Map formula node IDs to their evidence
        self.prob_evidence_per_formula = prob_evidence

    def layer2_formula(self, tree):
        self.visit_children(tree)

    @visit_children_decor
    def with_probability_evidence(self, items):
        return items[0]

    def probability_formula(self, tree: Tree):
        formula_tree = tree.children[0]
        relation = tree.children[1]
        threshold = Fraction(tree.children[2])

        formula_id = id(formula_tree)

        # Get evidence for this formula, if any
        evidence = self.prob_evidence_per_formula.get(formula_id, {})

        l1_transformer = Layer1BDDInterpreter(
            self.attack_tree, self.fault_tree, self.object_graph,
            reordering=False)
        bdd = l1_transformer.interpret(formula_tree)

        needed_vars = l1_transformer.object_properties.intersection(bdd.support)
        given_vars = set(self.configuration.keys())
        missing_vars = needed_vars - given_vars
        if len(missing_vars) > 0:
            raise MissingConfigurationError(missing_vars,
                                            type_name="object properties")
        self.used_object_properties.update(needed_vars)

        prob = l2_prob(self.attack_tree, self.fault_tree, bdd,
                       self.configuration, evidence)

        if evidence:
            evidence_str = ", ".join(f"{k}={v}" for k, v in evidence.items())
            print(f"INFO: Probability with evidence [{evidence_str}]: {prob}")
        else:
            print(
                f"INFO: Probability: {prob}")  # todo caz reconstruct the formula

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

    def impl_formula(self, tree):
        a, b = self.visit_children(tree)
        return (not a) or b

    def or_formula(self, tree):
        a, b = self.visit_children(tree)
        return a or b

    def and_formula(self, tree):
        a, b = self.visit_children(tree)
        return a and b

    def equiv_formula(self, tree):
        a, b = self.visit_children(tree)
        return a == b

    def nequiv_formula(self, tree):
        a, b = self.visit_children(tree)
        return a != b

    def neg_formula(self, tree):
        a, = self.visit_children(tree)
        return not a


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

    # First run a pre-pass to collect all probabilistic evidence from the parse tree
    evidence_interpreter = PrePassEvidenceInterpreter()
    evidence_interpreter.visit(formula.children[1])

    # Create the transformer and pass the collected evidence
    transformer = Layer2Interpreter(configuration, attack_tree, fault_tree,
                                    object_graph,
                                    evidence_interpreter.evidence_per_formula)

    res = transformer.visit(formula.children[1])

    surplus_vars = set(
        configuration.keys()) - transformer.used_object_properties
    if len(surplus_vars) > 0:
        # todo caz
        print(
            f"WARNING: You provided object properties in the configuration that"
            f" are not used in the formula, these can be removed: {surplus_vars}")

    return res
